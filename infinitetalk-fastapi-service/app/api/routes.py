"""API route definitions."""

import mimetypes
import os

from fastapi import APIRouter, BackgroundTasks
from fastapi import HTTPException
from fastapi.responses import FileResponse
from loguru import logger

from ..core.logging import get_log_content
from ..models.schemas import GenerateRequest
from ..services.command_executor import run_infinitetalk_command
from ..services.task_manager import task_manager

router = APIRouter()


@router.post("/generate")
async def generate_video(request: GenerateRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    if not task_manager.try_start():
        raise HTTPException(status_code=429, detail="Only one task can run at a time.")
    try:
        background_tasks.add_task(
            run_infinitetalk_command,
            request.input_json,
            request.save_file,
            task_manager,
        )
    except Exception:
        task_manager.finish_task()
        raise
    return {"status": "started"}


@router.get("/logs")
async def read_logs() -> dict[str, str]:
    return {"logs": get_log_content()}


UPLOAD_IMAGE_DIR = '../output_videos/'


@router.get("/download/video/{filename}")
async def download_file(filename: str):
    """下载文件（支持正确的 MIME 类型和文件名）"""
    try:
        #  根据文件类型确定路径和默认 MIME 类型
        file_config = {
            "video": {
                "dir": UPLOAD_IMAGE_DIR,
                "default_media_type": "video/mp4"
            }
        }
        #   构建文件路径
        file_path = UPLOAD_IMAGE_DIR + filename
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {filename}"
            )
        #   自动检测 MIME 类型（优先使用文件扩展名）
        media_type, _ = mimetypes.guess_type(str(file_path))
        # 如果检测失败，使用默认值
        if media_type is None:
            media_type = file_config['video']["default_media_type"]
        # 返回文件响应（带正确的 MIME 类型和下载文件名）
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
