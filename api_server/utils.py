import uuid
from datetime import datetime

from fastapi import UploadFile, HTTPException


# ==================== 辅助函数 ====================
def generate_unique_filename(prefix: str, extension: str) -> str:
    """生成唯一文件名"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"{prefix}_{timestamp}_{unique_id}{extension}"


def validate_file_size(file: UploadFile, max_size: int):
    """验证文件大小"""
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)"
        )