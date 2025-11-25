"""
FastAPI 应用：提供视频绿色背景去除服务

功能：
1. POST /convert - 转换视频格式并去除绿色背景
2. GET /logs/{filename} - 查看日志文件内容
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, field_validator


app = FastAPI(title="Green Background Removal Service")

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# 配置目录
OUTPUT_DIR = PROJECT_ROOT / "output_videos"
LOGS_DIR = PROJECT_ROOT / "logs"

# 确保目录存在
OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# 绿色背景去除脚本路径
SCRIPT_PATH = PROJECT_ROOT / "remove_green_background.py"


class ConvertRequest(BaseModel):
    """视频转换请求模型"""
    input: str
    output_format: str

    @field_validator('output_format')
    @classmethod
    def validate_output_format(cls, v: str) -> str:
        """验证输出格式"""
        if not v.startswith('.'):
            v = f'.{v}'
        return v


class ConvertResponse(BaseModel):
    """视频转换响应模型"""
    status: str
    message: str
    output_path: Optional[str] = None
    log_path: Optional[str] = None


@app.post("/convert", response_model=ConvertResponse)
async def convert_video(request: ConvertRequest):
    """
    转换视频格式并去除绿色背景
    
    Args:
        request: 包含输入路径和输出格式的请求
        
    Returns:
        转换结果信息
        
    Raises:
        HTTPException: 当参数验证失败时
    """
    input_path = Path(request.input)
    
    # 验证输入文件存在
    if not input_path.exists():
        raise HTTPException(status_code=404, detail=f"输入文件不存在: {request.input}")
    
    # 获取输入文件的后缀
    input_suffix = input_path.suffix.lower()
    
    # 验证输出格式与输入格式不同
    if request.output_format.lower() == input_suffix:
        raise HTTPException(
            status_code=400, 
            detail=f"输出格式 {request.output_format} 不能与输入文件后缀 {input_suffix} 相同"
        )
    
    # 构建输出路径
    output_filename = input_path.stem + request.output_format
    output_path = OUTPUT_DIR / output_filename
    
    # 如果输出文件已存在，直接返回成功
    if output_path.exists():
        log_filename = input_path.stem + '.log'
        return ConvertResponse(
            status="success",
            message="输出文件已存在，跳过转换",
            output_path=str(output_path),
            log_path=str(LOGS_DIR / log_filename)
        )
    
    # 构建日志文件路径
    log_filename = input_path.stem + '.log'
    log_path = LOGS_DIR / log_filename
    
    # 构建命令
    cmd = [
        sys.executable,  # 使用当前 Python 解释器
        str(SCRIPT_PATH),
        '--input', str(input_path),
        '--output', str(output_path),
        '--similarity', '0.35',
        '--blend', '0.1',
        '--despill-mix', '0.9',
        '--despill-expand', '0.1'
    ]
    
    # 在后台执行命令并重定向日志
    try:
        with open(log_path, 'w') as log_file:
            process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=str(PROJECT_ROOT),
                start_new_session=True  # 使进程在后台运行
            )
        
        return ConvertResponse(
            status="started",
            message=f"转换任务已启动，进程 PID: {process.pid}",
            output_path=str(output_path),
            log_path=str(log_path)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动转换任务失败: {str(e)}")


@app.get("/logs/{filename}", response_class=PlainTextResponse)
async def get_log_content(filename: str):
    """
    获取日志文件内容
    
    Args:
        filename: 日志文件名
        
    Returns:
        日志文件的文本内容
        
    Raises:
        HTTPException: 当日志文件不存在时返回 404
    """
    log_path = LOGS_DIR / filename
    
    if not log_path.exists():
        raise HTTPException(status_code=404, detail=f"日志文件不存在: {filename}")
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取日志文件失败: {str(e)}")


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok"}
