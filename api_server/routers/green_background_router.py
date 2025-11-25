"""
绿色背景去除服务 Router
提供视频绿色背景去除、任务管理和日志查询功能
"""
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, field_validator

from api_server.api_loger import logger
from api_server.config import config
# 创建路由器
router = APIRouter(prefix="/green_background", tags=["Green Background Removal"])

# ==================== 配置常量 ====================

# 配置目录
OUTPUT_DIR = config.BASE_DIR / "output_videos"
LOGS_DIR = config.BASE_DIR / "logs"

# 绿色背景去除脚本路径
SCRIPT_PATH = config.BASE_DIR / "remove_green_background.py"

# 确保目录存在
OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


# ==================== 数据模型 ====================

class ConvertRequest(BaseModel):
    """视频转换请求模型"""
    input: str
    output_format: str
    similarity: float = 0.35
    blend: float = 0.1
    despill_mix: float = 0.9
    despill_expand: float = 0.1

    @field_validator('output_format')
    @classmethod
    def validate_output_format(cls, v: str) -> str:
        """验证输出格式"""
        if not v.startswith('.'):
            v = f'.{v}'
        return v

    @field_validator('similarity', 'blend', 'despill_mix', 'despill_expand')
    @classmethod
    def validate_range(cls, v: float) -> float:
        """验证参数范围"""
        if not 0 <= v <= 1:
            raise ValueError('参数值必须在 0 到 1 之间')
        return v


class ConvertResponse(BaseModel):
    """视频转换响应模型"""
    status: str
    message: str
    task_id: Optional[str] = None
    output_path: Optional[str] = None
    log_path: Optional[str] = None
    pid: Optional[int] = None


class TaskStatus(BaseModel):
    """任务状态模型"""
    task_id: str
    status: str
    output_exists: bool
    log_exists: bool
    output_path: Optional[str] = None
    log_path: Optional[str] = None


# ==================== 辅助函数 ====================

def get_output_path(input_path: Path, output_format: str) -> Path:
    """构建输出路径"""
    output_filename = input_path.stem + output_format
    return OUTPUT_DIR / output_filename


def get_log_path(input_path: Path) -> Path:
    """构建日志路径"""
    log_filename = input_path.stem + '.log'
    return LOGS_DIR / log_filename


def validate_input_file(input_path: Path) -> None:
    """验证输入文件"""
    if not input_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"输入文件不存在: {input_path}"
        )
    
    if not input_path.is_file():
        raise HTTPException(
            status_code=400,
            detail=f"输入路径不是文件: {input_path}"
        )


def validate_output_format(input_path: Path, output_format: str) -> None:
    """验证输出格式与输入格式不同"""
    input_suffix = input_path.suffix.lower()
    if output_format.lower() == input_suffix:
        raise HTTPException(
            status_code=400,
            detail=f"输出格式 {output_format} 不能与输入文件后缀 {input_suffix} 相同"
        )


def build_command(
    input_path: Path,
    output_path: Path,
    similarity: float,
    blend: float,
    despill_mix: float,
    despill_expand: float
) -> list[str]:
    """构建绿幕去除命令"""
    return [
        sys.executable,  # 使用当前 Python 解释器
        str(SCRIPT_PATH),
        '--input', str(input_path),
        '--output', str(output_path),
        '--similarity', str(similarity),
        '--blend', str(blend),
        '--despill-mix', str(despill_mix),
        '--despill-expand', str(despill_expand)
    ]


# ==================== API 路由 ====================

@router.post(
    "/convert",
    response_model=ConvertResponse,
    summary="转换视频并去除绿色背景",
    description="提交视频绿幕去除任务，任务将在后台异步执行"
)
async def convert_video(request: ConvertRequest):
    """
    ## 🎬 视频绿幕去除服务
    
    ### 功能说明
    - 转换视频格式
    - 去除绿色背景
    - 支持自定义参数调节
    - 异步后台处理
    
    ### 参数说明
    - `input`: 输入视频文件路径
    - `output_format`: 输出格式（如 .webm, .mp4, .mov）
    - `similarity`: 绿色相似度阈值 (0-1)
    - `blend`: 边缘混合程度 (0-1)
    - `despill_mix`: 去绿边混合系数 (0-1)
    - `despill_expand`: 去绿边扩展范围 (0-1)
    
    ### 返回值
    - 如果输出文件已存在，直接返回
    - 否则启动后台任务，返回任务信息
    
    ### 示例
    ```bash
    POST /api/green_background/convert
    {
        "input": "/path/to/video.mov",
        "output_format": ".webm",
        "similarity": 0.35,
        "blend": 0.1
    }
    ```
    """
    try:
        input_path = Path(request.input)
        
        # 验证输入文件
        validate_input_file(input_path)
        
        # 验证输出格式
        validate_output_format(input_path, request.output_format)
        
        # 构建路径
        output_path = get_output_path(input_path, request.output_format)
        log_path = get_log_path(input_path)
        
        # 生成任务 ID
        task_id = input_path.stem
        
        # 如果输出文件已存在，直接返回
        if output_path.exists():
            logger.info(f"✅ 输出文件已存在: {output_path}")
            return ConvertResponse(
                status="completed",
                message="输出文件已存在，跳过转换",
                task_id=task_id,
                output_path=str(output_path),
                log_path=str(log_path) if log_path.exists() else None
            )
        
        # 构建命令
        cmd = build_command(
            input_path,
            output_path,
            request.similarity,
            request.blend,
            request.despill_mix,
            request.despill_expand
        )
        
        logger.info(f"🚀 启动绿幕去除任务: {task_id}")
        logger.debug(f"命令: {' '.join(cmd)}")
        
        # 在后台执行命令并重定向日志
        with open(log_path, 'w', encoding='utf-8') as log_file:
            process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=str(config.BASE_DIR),
                start_new_session=True  # 使进程在后台运行
            )
        
        logger.info(f"✅ 任务已启动，PID: {process.pid}")
        
        return ConvertResponse(
            status="started",
            message=f"转换任务已启动",
            task_id=task_id,
            output_path=str(output_path),
            log_path=str(log_path),
            pid=process.pid
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 启动转换任务失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"启动转换任务失败: {str(e)}"
        )


@router.get(
    "/status/{task_id}",
    response_model=TaskStatus,
    summary="查询任务状态",
    description="根据任务 ID 查询视频处理任务的状态"
)
async def get_task_status(task_id: str):
    """
    ## 📊 查询任务状态
    
    ### 功能说明
    根据任务 ID（通常为输入文件名）查询任务处理状态
    
    ### 参数
    - `task_id`: 任务 ID
    
    ### 返回值
    - `status`: 任务状态 (pending/processing/completed/failed)
    - `output_exists`: 输出文件是否存在
    - `log_exists`: 日志文件是否存在
    
    ### 示例
    ```bash
    GET /api/green_background/status/video_name
    ```
    """
    try:
        # 查找可能的输出文件（检查常见格式）
        possible_formats = ['.webm', '.mp4', '.mov', '.avi']
        output_path = None
        
        for fmt in possible_formats:
            candidate = OUTPUT_DIR / f"{task_id}{fmt}"
            if candidate.exists():
                output_path = candidate
                break
        
        log_path = LOGS_DIR / f"{task_id}.log"
        
        # 判断任务状态
        if output_path and output_path.exists():
            status = "completed"
        elif log_path.exists():
            status = "processing"
        else:
            status = "pending"
        
        return TaskStatus(
            task_id=task_id,
            status=status,
            output_exists=output_path is not None,
            log_exists=log_path.exists(),
            output_path=str(output_path) if output_path else None,
            log_path=str(log_path) if log_path.exists() else None
        )
        
    except Exception as e:
        logger.error(f"❌ 查询任务状态失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"查询任务状态失败: {str(e)}"
        )


@router.get(
    "/logs/{filename}",
    response_class=PlainTextResponse,
    summary="获取日志内容",
    description="获取指定任务的日志文件内容"
)
async def get_log_content(filename: str):
    """
    ## 📜 获取日志内容
    
    ### 功能说明
    获取任务执行的日志文件内容（纯文本格式）
    
    ### 参数
    - `filename`: 日志文件名（如 video_name.log）
    
    ### 返回值
    纯文本格式的日志内容
    
    ### 示例
    ```bash
    GET /api/green_background/logs/video_name.log
    ```
    """
    log_path = LOGS_DIR / filename
    
    if not log_path.exists():
        logger.warning(f"⚠️ 日志文件不存在: {filename}")
        raise HTTPException(
            status_code=404,
            detail=f"日志文件不存在: {filename}"
        )
    
    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        logger.info(f"✅ 读取日志文件: {filename} ({len(content)} bytes)")
        return content
        
    except Exception as e:
        logger.error(f"❌ 读取日志文件失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"读取日志文件失败: {str(e)}"
        )


@router.get(
    "/health",
    summary="健康检查",
    description="检查绿幕去除服务的健康状态"
)
async def health_check():
    """
    ## ❤️ 健康检查
    
    ### 功能说明
    检查服务状态和必要的依赖项
    
    ### 返回值
    - `status`: 服务状态
    - `script_exists`: 绿幕去除脚本是否存在
    - `output_dir`: 输出目录状态
    - `logs_dir`: 日志目录状态
    """
    return {
        "status": "ok",
        "service": "Green Background Removal",
        "script_exists": SCRIPT_PATH.exists(),
        "output_dir": {
            "path": str(OUTPUT_DIR),
            "exists": OUTPUT_DIR.exists(),
            "writable": os.access(OUTPUT_DIR, os.W_OK) if OUTPUT_DIR.exists() else False
        },
        "logs_dir": {
            "path": str(LOGS_DIR),
            "exists": LOGS_DIR.exists(),
            "writable": os.access(LOGS_DIR, os.W_OK) if LOGS_DIR.exists() else False
        }
    }