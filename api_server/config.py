import os
from pathlib import Path

from typing import Type


class Config:
    """基础配置类"""

    # ==================== 项目基础配置 ====================
    BASE_DIR = Path(__file__).parent.parent
    PROJECT_NAME = "InfiniteTalk"
    VERSION = "2.0.0"

    # ==================== MongoDB 数据库配置 ====================
    MONGO_URL = os.getenv(
        "MONGO_URL",
        "mongodb://admin:infinitetalk123@localhost:27017/infinitetalk_db?authSource=admin"
    )
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "infinitetalk_db")

    # MongoDB 集合名称
    COLLECTION_IMAGES = "images"
    COLLECTION_PROMPTS = "prompts"
    COLLECTION_AUDIOS = "audios"
    COLLECTION_TASKS = "tasks"

    # MongoDB 连接池配置
    MONGO_MAX_POOL_SIZE = 100
    MONGO_MIN_POOL_SIZE = 10
    MONGO_SERVER_SELECTION_TIMEOUT = 5000  # 毫秒

    # ==================== 日志配置 ====================

    # 日志级别（从环境变量或配置获取）
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # loguru 格式（注意：不要使用标准库的 % 格式）
    CONSOLE_FORMAT = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    FILE_FORMAT = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )

    # 日志目录和文件
    LOG_DIR = BASE_DIR / "logs"
    LOG_FILE = LOG_DIR / "infinitetalk.log"

    # ==================== 目录配置 ====================
    # 上传目录
    UPLOAD_IMAGE_DIR = BASE_DIR / "upload_image"
    AUDIO_FILE_DIR = BASE_DIR / "audio_file"

    # 输出目录
    OUTPUT_VIDEO_DIR = BASE_DIR / "output_videos"
    AUDIO_SAVE_DIR = BASE_DIR / "save_audio"
    OUTPUTS_DIR = BASE_DIR / "outputs"

    # 示例文件目录
    EXAMPLES_DIR = BASE_DIR / "examples"

    # 权重文件目录
    WEIGHTS_DIR = BASE_DIR / "weights"

    # 备份目录
    BACKUP_DIR = BASE_DIR / "backups"

    # ==================== 模型权重路径配置 ====================
    # Wan2.1 主模型
    MODEL_CKPT_DIR = WEIGHTS_DIR / "Wan2.1-I2V-14B-480P"

    # Wav2Vec2 音频编码器
    WAV2VEC_DIR = WEIGHTS_DIR / "chinese-wav2vec2-base"

    # InfiniteTalk 权重
    INFINITETALK_DIR = WEIGHTS_DIR / "InfiniteTalk" / "single" / "infinitetalk.safetensors"

    # 量化模型权重
    QUANT_DIR = WEIGHTS_DIR / "InfiniteTalk" / "quant_models" / "infinitetalk_single_fp8.safetensors"

    # DiT 模型路径（可选）
    DIT_PATH = None

    # ==================== 模型配置 ====================
    # 任务类型
    TASK = "infinitetalk-14B"

    # 模型大小配置
    MODEL_SIZE = "infinitetalk-480"  # 可选: infinitetalk-480, infinitetalk-720

    # 量化类型
    MODEL_QUANT = "fp8"  # 可选: fp8, int8, bf16, fp16, None

    # 模型设备配置
    MODEL_DEVICE_ID = 0  # GPU 设备 ID
    MODEL_RANK = 0

    # FSDP 配置
    USE_T5_FSDP = False
    USE_DIT_FSDP = False
    USE_T5_CPU = False

    # 并行配置
    ULYSSES_SIZE = 1  # DiT 中的 Ulysses 并行大小
    RING_SIZE = 1  # DiT 中的 Ring Attention 并行大小

    # USP 配置
    USE_USP = False

    # LoRA 配置
    LORA_DIR = None  # 可以是单个路径或路径列表
    LORA_SCALES = [1.2]  # 对应每个 LoRA 的缩放因子

    # DiT 参数持久化配置
    NUM_PERSISTENT_PARAM_IN_DIT = 0  # 显存中保留的最大参数量

    # ==================== 生成参数配置 ====================
    # 视频生成参数
    MOTION_FRAME = 9  # 运动帧数（长视频生成模式使用）
    FRAME_NUM = 81  # 单个片段生成的帧数（应该是 4n+1）
    MAX_FRAMES_NUM = 1000  # 生成视频的最大帧长度

    # 生成模式
    GENERATION_MODE = "streaming"  # 可选: clip（生成一个视频片段）, streaming（长视频生成）

    # 采样参数
    SAMPLE_SHIFT = 7.0  # Flow matching 调度器的采样偏移因子
    SAMPLE_STEPS = 40  # 采样步数
    sample_text_guide_scale = 5.0  # 文本控制的分类器自由引导强度

    # 引导参数
    TEXT_GUIDE_SCALE = 5.0  # 文本控制的分类器自由引导强度
    AUDIO_GUIDE_SCALE = 4.0  # 音频控制的分类器自由引导强度

    # 种子配置
    DEFAULT_SEED = 42  # 基础随机种子
    SEED = None  # 当前使用的种子（None 表示使用 DEFAULT_SEED）

    # 颜色校正
    COLOR_CORRECTION_STRENGTH = 1.0  # 颜色校正强度 [0.0 -- 1.0]

    # 模型卸载
    OFFLOAD_MODEL = True  # 是否在每次模型前向传播后卸载到 CPU 以减少显存使用

    # 高质量保存
    HIGH_QUALITY_SAVE = False  # 高质量保存
    base_seed = 42 # 基础随机种子The seed to use for generating the image or video.

    # ==================== TeaCache 配置 ====================
    USE_TEACACHE = False  # 启用 TeaCache 加速视频生成
    TEACACHE_THRESH = 0.2  # TeaCache 阈值

    # ==================== APG (自适应投影引导) 配置 ====================
    USE_APG = False  # 启用自适应投影引导
    APG_MOMENTUM = -0.75  # APG 动量
    APG_NORM_THRESHOLD = 55  # APG 范数阈值

    # ==================== 音频处理配置 ====================
    AUDIO_SAMPLE_RATE = 16000  # 音频采样率
    AUDIO_LOUDNESS_NORM = True  # 是否进行响度归一化
    AUDIO_MODE = "localfile"  # 可选: localfile（本地 wav 文件）, tts（TTS 生成）
    sample_audio_guide_scale = 4.0  # 音频控制的分类器自由引导强度

    # ==================== 场景分割配置 ====================
    SCENE_SEGMENTATION = False  # 为输入视频启用场景分割

    # ==================== API 服务配置 ====================
    # 服务器配置
    API_HOST = "0.0.0.0"
    API_PORT = 50002
    API_WORKERS = 1

    # API 文档配置
    API_TITLE = "InfiniteTalk API"
    API_DESCRIPTION = "InfiniteTalk 视频生成 API 服务"
    API_VERSION = "1.0.0"

    # CORS 配置
    ENABLE_CORS = True
    CORS_ORIGINS = ["*"]  # 生产环境应该设置具体的域名
    CORS_CREDENTIALS = True
    CORS_METHODS = ["*"]
    CORS_HEADERS = ["*"]

    # ==================== 文件上传限制 ====================
    # 最大文件大小（字节）
    MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_AUDIO_SIZE = 50 * 1024 * 1024  # 50MB

    # 允许的文件扩展名
    ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
    ALLOWED_AUDIO_EXTENSIONS = {'.wav', '.mp3', '.m4a', '.flac', '.ogg'}
    ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv'}

    # ==================== 任务队列配置 ====================
    # 并发任务数量
    MAX_CONCURRENT_TASKS = 2

    # 任务超时时间（秒）
    TASK_TIMEOUT = 3600  # 1小时

    # 任务清理配置
    AUTO_CLEANUP_TASKS = True
    TASK_RETENTION_DAYS = 7  # 保留天数


    # ==================== 性能优化配置 ====================
    # 缓存配置
    ENABLE_CACHE = True
    CACHE_TTL = 3600  # 缓存过期时间（秒）

    # 预加载模型
    PRELOAD_MODELS = True

    # GPU 内存管理
    GPU_MEMORY_FRACTION = 0.9  # 使用 90% 的 GPU 内存

    # ==================== 安全配置 ====================
    # API 密钥（生产环境应该设置）
    API_KEY = os.getenv("API_KEY", None)

    # 速率限制
    ENABLE_RATE_LIMIT = False
    RATE_LIMIT_PER_MINUTE = 60

    # ==================== 环境配置 ====================
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")  # development, production, testing
    DEBUG = ENVIRONMENT == "development"

    # 时区
    TIMEZONE = os.getenv("TZ", "Asia/Shanghai")

    @classmethod
    def init_directories(cls):
        """初始化所有必要的目录"""
        directories = [
            cls.UPLOAD_IMAGE_DIR,
            cls.AUDIO_FILE_DIR,
            cls.OUTPUT_VIDEO_DIR,
            cls.AUDIO_SAVE_DIR,
            cls.OUTPUTS_DIR,
            cls.BACKUP_DIR,
            cls.LOG_DIR,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_model_config(cls) -> dict:
        """获取模型配置字典"""
        return {
            "task": cls.TASK,
            "ckpt_dir": str(cls.MODEL_CKPT_DIR) if cls.MODEL_CKPT_DIR else None,
            "wav2vec_dir": str(cls.WAV2VEC_DIR) if cls.WAV2VEC_DIR else None,
            "infinitetalk_dir": str(cls.INFINITETALK_DIR) if cls.INFINITETALK_DIR else None,
            "quant_dir": str(cls.QUANT_DIR) if cls.QUANT_DIR else None,
            "dit_path": str(cls.DIT_PATH) if cls.DIT_PATH else None,
            "size": cls.MODEL_SIZE,
            "quant": cls.MODEL_QUANT,
            "device_id": cls.MODEL_DEVICE_ID,
            "rank": cls.MODEL_RANK,
            "t5_fsdp": cls.USE_T5_FSDP,
            "dit_fsdp": cls.USE_DIT_FSDP,
            "t5_cpu": cls.USE_T5_CPU,
            "use_usp": cls.USE_USP,
            "lora_dir": cls.LORA_DIR,
            "lora_scales": cls.LORA_SCALES,
            "offload_model": cls.OFFLOAD_MODEL,
            "ulysses_size": cls.ULYSSES_SIZE,
            "ring_size": cls.RING_SIZE,
            "num_persistent_param_in_dit": cls.NUM_PERSISTENT_PARAM_IN_DIT,
        }

    @classmethod
    def get_generation_config(cls) -> dict:
        """获取生成参数配置字典"""
        return {
            "motion_frame": cls.MOTION_FRAME,
            "frame_num": cls.FRAME_NUM,
            "max_frames_num": cls.MAX_FRAMES_NUM,
            "shift": cls.SAMPLE_SHIFT,
            "sampling_steps": cls.SAMPLE_STEPS,
            "text_guide_scale": cls.TEXT_GUIDE_SCALE,
            "audio_guide_scale": cls.AUDIO_GUIDE_SCALE,
            "seed": cls.SEED if cls.SEED is not None else cls.DEFAULT_SEED,
            "offload_model": cls.OFFLOAD_MODEL,
            "color_correction_strength": cls.COLOR_CORRECTION_STRENGTH,
            "mode": cls.GENERATION_MODE,
        }

    @classmethod
    def get_extra_args(cls):
        """获取额外参数（类似 argparse.Namespace）"""
        from types import SimpleNamespace
        return SimpleNamespace(
            use_teacache=cls.USE_TEACACHE,
            teacache_thresh=cls.TEACACHE_THRESH,
            use_apg=cls.USE_APG,
            apg_momentum=cls.APG_MOMENTUM,
            apg_norm_threshold=cls.APG_NORM_THRESHOLD,
            seed=cls.SEED if cls.SEED is not None else cls.DEFAULT_SEED,
            audio_mode=cls.AUDIO_MODE,
            scene_seg=cls.SCENE_SEGMENTATION,
        )

    @classmethod
    def validate_config(cls):
        """验证配置是否正确"""
        errors = []

        # 检查必要的目录
        if not cls.WEIGHTS_DIR.exists():
            errors.append(f"Weights directory not found: {cls.WEIGHTS_DIR}")

        # 检查模型文件
        if cls.MODEL_CKPT_DIR and not cls.MODEL_CKPT_DIR.exists():
            errors.append(f"Model checkpoint directory not found: {cls.MODEL_CKPT_DIR}")

        if cls.WAV2VEC_DIR and not cls.WAV2VEC_DIR.exists():
            errors.append(f"Wav2Vec directory not found: {cls.WAV2VEC_DIR}")

        # 检查 MongoDB URL
        if not cls.MONGO_URL:
            errors.append("MONGO_URL is not set")

        # 检查量化类型
        if cls.MODEL_QUANT and cls.MODEL_QUANT not in ['int8', 'fp8', 'bf16', 'fp16']:
            errors.append(f"Invalid quantization type: {cls.MODEL_QUANT}")

        # 检查 frame_num
        if (cls.FRAME_NUM - 1) % 4 != 0:
            errors.append(f"FRAME_NUM should be 4n+1, got {cls.FRAME_NUM}")

        if errors:
            raise ValueError(f"Configuration validation failed:\n" + "\n".join(errors))

        return True


# 开发环境配置
class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    LOG_LEVEL = "DEBUG"


# 生产环境配置
class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    LOG_LEVEL = "WARNING"
    OFFLOAD_MODEL = True
    ENABLE_RATE_LIMIT = True


# 测试环境配置
class TestingConfig(Config):
    """测试环境配置"""
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    MONGO_DB_NAME = "infinitetalk_test_db"


# 根据环境变量选择配置
def get_config() -> Type[Config]:
    """根据环境变量获取配置"""
    env = os.getenv("ENVIRONMENT", "development").lower()

    config_map = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig,
    }

    return config_map.get(env, DevelopmentConfig)


# 导出当前配置
config = get_config()

# 初始化目录
config.init_directories()
