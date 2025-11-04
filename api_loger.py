import logging
import sys

from config import config

# ==================== 配置日志 ====================
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT,
    datefmt=config.LOG_DATE_FORMAT,
    handlers=[
        logging.StreamHandler(stream=sys.stdout),
        logging.FileHandler(config.LOG_FILE) if config.LOG_FILE.parent.exists() else logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

