"""
使用 loguru 配置日志系统
"""
import sys

from loguru import logger

from api_server.config import config

# 移除默认的 handler
logger.remove()

# 添加控制台输出
logger.add(
    sys.stdout,
    format=config.CONSOLE_FORMAT,
    level=config.LOG_LEVEL,
    colorize=True,
    backtrace=True,
    diagnose=True
)

# 添加文件输出
try:
    logger.add(
        str(config.LOG_FILE),
        format=config.FILE_FORMAT,
        level=config.LOG_LEVEL,
        rotation="500 MB",  # 文件大小超过 500MB 时轮转
        retention="30 days",  # 保留 30 天
        compression="zip",  # 压缩旧日志
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
        enqueue=True  # 异步写入，避免阻塞
    )
except Exception as e:
    print(f"Warning: Could not set up file logging: {e}", file=sys.stderr)

# 可选：添加错误日志单独文件
try:
    error_log_file = config.LOG_DIR / f"{config.LOG_FILE.stem}_error.log"
    logger.add(
        str(error_log_file),
        format=config.FILE_FORMAT,
        level="ERROR",
        rotation="100 MB",
        retention="60 days",
        compression="zip",
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
        enqueue=True
    )
except Exception as e:
    print(f"Warning: Could not set up error logging: {e}", file=sys.stderr)

# 导出 logger
__all__ = ['logger']
