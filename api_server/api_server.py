import asyncio
import mimetypes
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api_server.api_loger import logger
from api_server.config import config
from api_server.database import db_manager
from api_server.models import ImageInfo, TaskInfo, PromptInfo, AudioInfo
from api_server.utils import generate_unique_filename, validate_file_size
from api_server.video_task_worker import video_task_worker


# ==================== 生命周期管理 ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    try:
        logger.info("=" * 60)
        logger.info(f"Starting {config.PROJECT_NAME} API Server v{config.VERSION}")
        logger.info(f"Environment: {config.ENVIRONMENT}")
        logger.info("=" * 60)

        # 验证配置
        logger.info("Validating configuration...")
        config.validate_config()
        logger.info("✓ Configuration validated")

        # 连接数据库
        logger.info("Connecting to database...")
        await db_manager.connect()
        logger.info("✓ Database connected")
        # 启动任务处理器
        asyncio.create_task(video_task_worker.start())

        logger.info("=" * 60)
        logger.info(f"{config.PROJECT_NAME} API server started successfully")
        logger.info(f"API Documentation: http://{config.API_HOST}:{config.API_PORT}/docs")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise

    yield  # 应用运行期间

    # 关闭时执行
    logger.info("Shutting down server...")
    await db_manager.disconnect()
    logger.info("Server shutdown complete")

    # 关闭时
    logger.info("Shutting down video_task_worker...")
    await video_task_worker.stop()
    logger.info("Shutting down video_task_worker complete")

# ==================== 创建 FastAPI 应用 ====================
app = FastAPI(
    title=config.API_TITLE,
    description=config.API_DESCRIPTION,
    version=config.API_VERSION,
    debug=config.DEBUG,
    lifespan=lifespan
)

# 配置 CORS
if config.ENABLE_CORS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=config.CORS_CREDENTIALS,
        allow_methods=config.CORS_METHODS,
        allow_headers=config.CORS_HEADERS,
    )




# ==================== API 接口 ====================

# 1. 图片上传接口
@app.post("/api/images/upload", response_model=dict)
async def upload_image(
        person_name: str = Form(...),
        image: UploadFile = File(...)
):
    """上传图片"""
    try:
        # 验证文件类型
        file_extension = Path(image.filename).suffix.lower()
        if file_extension not in config.ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {config.ALLOWED_IMAGE_EXTENSIONS}"
            )

        # 验证文件大小
        validate_file_size(image, config.MAX_IMAGE_SIZE)

        # 生成唯一文件名
        unique_filename = generate_unique_filename("img", file_extension)
        image_path = config.UPLOAD_IMAGE_DIR / unique_filename

        # 保存文件
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        # 保存到数据库
        image_id = await db_manager.create_image(
            person_name=person_name,
            image_name=image.filename,
            image_path=str(image_path)
        )

        logger.info(f"Image uploaded: {image_id} - {image.filename}")

        return {
            "success": True,
            "image_id": image_id,
            "image_path": str(image_path),
            "message": "Image uploaded successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 2. 图片查询接口（按ID）
@app.get("/api/images/{image_id}", response_model=ImageInfo)
async def get_image_by_id(image_id: str):
    """根据ID查询图片信息"""
    try:
        image_doc = await db_manager.get_image_by_id(image_id)
        if not image_doc:
            raise HTTPException(status_code=404, detail="Image not found")
        return image_doc
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 3. 图片列表查询（按人物名称模糊匹配）
@app.get("/api/images", response_model=List[ImageInfo])
async def search_images(person_name: Optional[str] = None, limit: int = 100):
    """根据人物名称模糊搜索图片"""
    try:
        images = await db_manager.search_images(person_name, limit)
        return images
    except Exception as e:
        logger.error(f"Error searching images: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 4. 删除图片接口
@app.delete("/api/images/{image_id}", response_model=dict)
async def delete_image(image_id: str):
    """删除图片"""
    try:
        # 先获取图片信息
        image_doc = await db_manager.get_image_by_id(image_id)
        if not image_doc:
            raise HTTPException(status_code=404, detail="Image not found")

        # 删除文件
        image_path = Path(image_doc['image_path'])
        if image_path.exists():
            image_path.unlink()

        # 删除数据库记录
        success = await db_manager.delete_image(image_id)

        if success:
            logger.info(f"Image deleted: {image_id}")
            return {"success": True, "message": "Image deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete image")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 5. 提示词上传接口
@app.post("/api/prompts/upload", response_model=dict)
async def upload_prompt(
        title: str = Form(...),
        content: str = Form(...)
):
    """上传提示词"""
    try:
        prompt_id = await db_manager.create_prompt(title, content)

        logger.info(f"Prompt uploaded: {prompt_id} - {title}")

        return {
            "success": True,
            "prompt_id": prompt_id,
            "message": "Prompt uploaded successfully"
        }
    except Exception as e:
        logger.error(f"Error uploading prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 6. 提示词查询接口（按ID）
@app.get("/api/prompts/{prompt_id}", response_model=PromptInfo)
async def get_prompt_by_id(prompt_id: str):
    """根据ID查询提示词"""
    try:
        prompt_doc = await db_manager.get_prompt_by_id(prompt_id)
        if not prompt_doc:
            raise HTTPException(status_code=404, detail="Prompt not found")
        return prompt_doc
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 7. 提示词查询接口（按标题模糊匹配）
@app.get("/api/prompts", response_model=List[PromptInfo])
async def search_prompts(title: Optional[str] = None, limit: int = 100):
    """根据标题模糊搜索提示词"""
    try:
        prompts = await db_manager.search_prompts(title, limit)
        return prompts
    except Exception as e:
        logger.error(f"Error searching prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 8. 删除提示词接口
@app.delete("/api/prompts/{prompt_id}", response_model=dict)
async def delete_prompt(prompt_id: str):
    """删除提示词"""
    try:
        success = await db_manager.delete_prompt(prompt_id)

        if success:
            logger.info(f"Prompt deleted: {prompt_id}")
            return {"success": True, "message": "Prompt deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Prompt not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 9. 音频文件上传接口
@app.post("/api/audio/upload", response_model=dict)
async def upload_audio(
        audio_text: str = Form(...),
        audio_file: UploadFile = File(...)
):
    """上传音频文件"""
    try:
        # 验证文件类型
        file_extension = Path(audio_file.filename).suffix.lower()
        if file_extension not in config.ALLOWED_AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {config.ALLOWED_AUDIO_EXTENSIONS}"
            )

        # 验证文件大小
        validate_file_size(audio_file, config.MAX_AUDIO_SIZE)

        # 生成唯一ID和文件名
        audio_id = uuid.uuid4().hex
        unique_filename = generate_unique_filename("audio", file_extension)
        audio_path = config.AUDIO_FILE_DIR / unique_filename

        # 保存文件
        with open(audio_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)

        # 保存到数据库
        await db_manager.create_audio(
            audio_id=audio_id,
            audio_path=str(audio_path),
            audio_text=audio_text,
            original_filename=audio_file.filename
        )

        logger.info(f"Audio uploaded: {audio_id} - {audio_file.filename}")

        return {
            "success": True,
            "audio_id": audio_id,
            "audio_path": str(audio_path),
            "message": "Audio uploaded successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 10. 音频查询接口（按ID）
@app.get("/api/audio/{audio_id}", response_model=AudioInfo)
async def get_audio_by_id(audio_id: str):
    """根据ID查询音频信息"""
    try:
        audio_doc = await db_manager.get_audio_by_id(audio_id)
        if not audio_doc:
            raise HTTPException(status_code=404, detail="Audio not found")
        return audio_doc
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 11. 音频列表接口（最新N个）
@app.get("/api/audio", response_model=List[AudioInfo])
async def get_recent_audios(limit: int = 10):
    """获取最新的音频列表"""
    try:
        audios = await db_manager.get_recent_audios(limit)
        return audios
    except Exception as e:
        logger.error(f"Error getting audio list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 12. 删除音频接口
@app.delete("/api/audio/{audio_id}", response_model=dict)
async def delete_audio(audio_id: str):
    """删除音频"""
    try:
        # 先获取音频信息
        audio_doc = await db_manager.get_audio_by_id(audio_id)
        if not audio_doc:
            raise HTTPException(status_code=404, detail="Audio not found")

        # 删除文件
        audio_path = Path(audio_doc['audio_path'])
        if audio_path.exists():
            audio_path.unlink()

        # 删除数据库记录
        success = await db_manager.delete_audio(audio_id)

        if success:
            logger.info(f"Audio deleted: {audio_id}")
            return {"success": True, "message": "Audio deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete audio")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 13. 下载文件接口（通用）
@app.get("/api/download/{file_type}/{filename}")
async def download_file(file_type: str, filename: str):
    """下载文件（支持正确的 MIME 类型和文件名）"""
    try:
        # 1️⃣ 根据文件类型确定路径和默认 MIME 类型
        file_config = {
            "image": {
                "dir": config.UPLOAD_IMAGE_DIR,
                "default_media_type": "image/jpeg"
            },
            "audio": {
                "dir": config.AUDIO_FILE_DIR,
                "default_media_type": "audio/mpeg"
            },
            "video": {
                "dir": config.OUTPUT_VIDEO_DIR,
                "default_media_type": "video/mp4"
            }
        }
        if file_type not in file_config:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Must be one of: {', '.join(file_config.keys())}"
            )
        # 2️⃣ 构建文件路径
        file_path = file_config[file_type]["dir"] / filename
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {filename}"
            )
        # 3️⃣ 自动检测 MIME 类型（优先使用文件扩展名）
        media_type, _ = mimetypes.guess_type(str(file_path))
        # 如果检测失败，使用默认值
        if media_type is None:
            media_type = file_config[file_type]["default_media_type"]
        # 4️⃣ 返回文件响应（带正确的 MIME 类型和下载文件名）
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename  # ✅ 设置下载时的文件名
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 视频生成相关接口 ====================
# 14. 创建视频生成任务
@app.post("/api/tasks/create", response_model=TaskInfo)
async def create_video_task(
        prompt: str = Form(...),
        image_path: str = Form(...),
        audio_path: str = Form(...)
):
    """创建视频生成任务（立即返回任务ID，后台异步生成）"""
    try:
        # 验证文件是否存在
        if not Path(image_path).exists():
            raise HTTPException(status_code=400, detail="Image file not found")
        if not Path(audio_path).exists():
            raise HTTPException(status_code=400, detail="Audio file not found")
        # 创建任务ID
        task_id = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        # 保存任务到数据库
        await db_manager.create_task(
            task_id=task_id,
            prompt=prompt,
            image_path=image_path,
            audio_path=audio_path
        )
        # 添加到任务队列
        await video_task_worker.add_task(task_id)
        logger.info(f"Task created: {task_id}")
        # 返回任务信息
        task_info = await db_manager.get_task_by_id(task_id)
        return task_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 15. 查询任务状态
@app.get("/api/tasks/{task_id}", response_model=TaskInfo)
async def get_task_status(task_id: str):
    """查询任务状态"""
    try:
        task_doc = await db_manager.get_task_by_id(task_id)
        if not task_doc:
            raise HTTPException(status_code=404, detail="Task not found")
        return task_doc
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 16. 获取任务列表
@app.get("/api/tasks", response_model=List[TaskInfo])
async def get_tasks(
        status: Optional[str] = None,
        limit: int = 20
):
    """获取任务列表"""
    try:
        tasks = await db_manager.get_tasks(status, limit)
        return tasks
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 17. 删除任务
@app.delete("/api/tasks/{task_id}", response_model=dict)
async def delete_task(task_id: str):
    """删除任务"""
    try:
        # 先获取任务信息
        task_doc = await db_manager.get_task_by_id(task_id)
        if not task_doc:
            raise HTTPException(status_code=404, detail="Task not found")
        # 删除视频文件（如果存在）
        if task_doc.get('video_path'):
            video_path = Path(task_doc['video_path'])
            if video_path.exists():
                video_path.unlink()
        # 删除音频保存目录
        task_audio_dir = config.AUDIO_SAVE_DIR / task_id
        if task_audio_dir.exists():
            shutil.rmtree(task_audio_dir)
        # 删除数据库记录
        success = await db_manager.delete_task(task_id)
        if success:
            logger.info(f"Task deleted: {task_id}")
            return {"success": True, "message": "Task deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete task")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 系统相关接口 ====================
# 18. 健康检查
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "project": config.PROJECT_NAME,
        "version": config.VERSION,
        "environment": config.ENVIRONMENT,
        "timestamp": datetime.now().isoformat()
    }


# 19. 系统信息
@app.get("/api/info")
async def get_system_info():
    """获取系统信息"""
    return {
        "project": config.PROJECT_NAME,
        "version": config.VERSION,
        "api_version": config.API_VERSION,
        "environment": config.ENVIRONMENT,
        "models": {
            "model_size": config.MODEL_SIZE,
            "quantization": config.MODEL_QUANT,
        },
        "limits": {
            "max_image_size": config.MAX_IMAGE_SIZE,
            "max_audio_size": config.MAX_AUDIO_SIZE,
            "allowed_image_formats": list(config.ALLOWED_IMAGE_EXTENSIONS),
            "allowed_audio_formats": list(config.ALLOWED_AUDIO_EXTENSIONS),
        },
        "timestamp": datetime.now().isoformat()
    }


# 20. 配置信息（仅开发环境）
@app.get("/api/config")
async def get_config_info():
    """获取配置信息（仅开发环境）"""
    if not config.DEBUG:
        raise HTTPException(status_code=403, detail="Not available in production")

    return {
        "environment": config.ENVIRONMENT,
        "debug": config.DEBUG,
        "model": {
            "size": config.MODEL_SIZE,
            "quant": config.MODEL_QUANT,
            "device_id": config.MODEL_DEVICE_ID,
        },
        "generation": {
            "motion_frame": config.MOTION_FRAME,
            "frame_num": config.FRAME_NUM,
            "max_frames": config.MAX_FRAMES_NUM,
            "sample_steps": config.SAMPLE_STEPS,
            "text_guide_scale": config.TEXT_GUIDE_SCALE,
            "audio_guide_scale": config.AUDIO_GUIDE_SCALE,
        },
        "audio": {
            "sample_rate": config.AUDIO_SAMPLE_RATE,
        },
        "api": {
            "host": config.API_HOST,
            "port": config.API_PORT,
            "cors_enabled": config.ENABLE_CORS,
        },
        "tasks": {
            "max_concurrent": config.MAX_CONCURRENT_TASKS,
            "timeout": config.TASK_TIMEOUT,
            "retention_days": config.TASK_RETENTION_DAYS,
        }
    }


# 21. 清理旧任务（管理接口）
@app.post("/api/admin/cleanup", response_model=dict)
async def cleanup_old_tasks(days: Optional[int] = None):
    """清理旧任务（管理接口）"""
    if not config.DEBUG:
        raise HTTPException(status_code=403, detail="Not available in production")

    try:
        deleted_count = await db_manager.cleanup_old_tasks(days)
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Cleaned up {deleted_count} old tasks"
        }
    except Exception as e:
        logger.error(f"Error cleaning up tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 根路径 ====================
@app.get("/")
async def root():
    """API 根路径"""
    return {
        "message": f"Welcome to {config.PROJECT_NAME} API",
        "version": config.API_VERSION,
        "documentation": "/docs",
        "health": "/health",
        "info": "/api/info"
    }


# ==================== 启动服务 ====================
def main():
    import uvicorn

    uvicorn.run(
        app,
        host=config.API_HOST,
        port=config.API_PORT,
        workers=config.API_WORKERS,
        log_level=config.LOG_LEVEL.lower()
    )
