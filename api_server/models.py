from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class ImageInfo(BaseModel):
    id: str
    person_name: str
    image_name: str
    image_path: str
    created_at: datetime


class PromptInfo(BaseModel):
    id: str
    title: str
    content: str
    created_at: datetime


class AudioInfo(BaseModel):
    id: str
    audio_path: str
    audio_text: str
    original_filename: str
    created_at: datetime


class TaskProgress(BaseModel):
    """任务进度信息"""
    stage: str = "pending"  # pending, loading, preprocessing, generating, postprocessing, completed
    progress: int = 0  # 0-100
    message: str = ""
    updated_at: datetime = Field(default_factory=datetime.now)


class TaskLog(BaseModel):
    """单条日志"""
    timestamp: datetime = Field(default_factory=datetime.now)
    level: str = "INFO"  # INFO, WARNING, ERROR
    message: str


class TaskInfo(BaseModel):
    """任务信息"""
    id: str
    status: str = "pending"  # pending, processing, running, completed, failed
    prompt: str
    image_path: str
    audio_path: str
    generate_video_file: Optional[str] = None
    video_download_url: Optional[str] = None

    # 进程信息
    pid: Optional[int] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    # 进度信息（新增）
    progress: Optional[TaskProgress] = None

    # 日志信息（新增）
    logs: List[TaskLog] = Field(default_factory=list)
    log_path : Optional[str] = None
    json_path: Optional[str] = None

    # 错误信息
    error_message: Optional[str] = None

    # 时间戳
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    # 运行时长
    uptime: Optional[float] = None  # 以秒为单位
