# api_logger.py
"""
使用 loguru 配置日志系统
"""
import sys
from pathlib import Path
from loguru import logger

from api_server.config import config

# 移除默认的 handler
logger.remove()

# 添加控制台输出
logger.add(
    sys.stdout,
    format=config.LOG_FORMAT if hasattr(config, 'LOG_FORMAT') else
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>",
    level=config.LOG_LEVEL,
    colorize=True,
    backtrace=True,
    diagnose=True
)

# 添加文件输出
if config.LOG_FILE.parent.exists() or config.LOG_FILE.parent == Path('.'):
    # 确保日志目录存在
    config.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        str(config.LOG_FILE),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        level=config.LOG_LEVEL,
        rotation="500 MB",  # 文件大小超过 500MB 时轮转
        retention="30 days",  # 保留 30 天
        compression="zip",  # 压缩旧日志
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
        enqueue=True  # 异步写入
    )

# 可选：添加错误日志单独文件
error_log_file = config.LOG_FILE.parent / f"{config.LOG_FILE.stem}_error.log"
logger.add(
    str(error_log_file),
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
    level="ERROR",
    rotation="100 MB",
    retention="60 days",
    compression="zip",
    encoding="utf-8",
    backtrace=True,
    diagnose=True,
    enqueue=True
)

# 导出 logger
__all__ = ['logger']