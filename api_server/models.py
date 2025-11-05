from typing import Optional

from pydantic import BaseModel
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


class TaskInfo(BaseModel):
    id: str
    status: str
    prompt: str
    image_path: str
    audio_path: str
    video_path: Optional[str] = None
    video_download_url: Optional[str] = None
    task_failed: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    # 新增字段
    pid: Optional[int] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    task_execute_info: Optional[str] = None
