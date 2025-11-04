import asyncio
from datetime import datetime
from pathlib import Path

import soundfile as sf
import torch

# 导入原有的生成逻辑
import wan
from api_loger import logger
from config import config
from database import db_manager
# 从原文件导入需要的函数
from generate_infinitetalk import (
    audio_prepare_single,
    get_embedding,
    custom_init
)
from wan.configs import WAN_CONFIGS
from wan.utils.multitalk_utils import save_video_ffmpeg

# 全局变量
wan_pipeline = None
wav2vec_feature_extractor = None
audio_encoder = None


async def init_models():
    """初始化InfiniteTalk模型"""
    global wan_pipeline, wav2vec_feature_extractor, audio_encoder

    try:
        logger.info("Initializing Wav2Vec2 model...")

        # 初始化 wav2vec
        wav2vec_feature_extractor, audio_encoder = custom_init(
            'cpu',
            str(config.WAV2VEC_DIR)
        )
        logger.info("✓ Wav2Vec2 initialized")

        # 获取模型配置
        logger.info("Initializing InfiniteTalk pipeline...")
        model_cfg = config.get_model_config()
        cfg = WAN_CONFIGS["infinitetalk-14B"]

        # 初始化 InfiniteTalk pipeline
        wan_pipeline = wan.InfiniteTalkPipeline(
            config=cfg,
            checkpoint_dir=model_cfg['ckpt_dir'],
            quant_dir=model_cfg['quant_dir'],
            device_id=model_cfg['device_id'],
            rank=model_cfg['rank'],
            t5_fsdp=model_cfg['t5_fsdp'],
            dit_fsdp=model_cfg['dit_fsdp'],
            use_usp=model_cfg['use_usp'],
            t5_cpu=model_cfg['t5_cpu'],
            lora_dir=model_cfg['lora_dir'],
            lora_scales=model_cfg['lora_scales'],
            quant=model_cfg['quant'],
            dit_path=None,
            infinitetalk_dir=model_cfg['infinitetalk_dir']
        )
        logger.info("✓ InfiniteTalk pipeline initialized")

        logger.info("All models initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize models: {e}")
        raise


# ==================== 视频生成引擎 ====================
class VideoEngine:
    def __init__(self):
        self.pipeline = None
        self.wav2vec_feature_extractor = None
        self.audio_encoder = None

    async def initialize(self):
        """初始化视频生成模型"""
        try:
            logger.info("正在加载视频生成模型...")

            loop = asyncio.get_event_loop()

            # 在线程池中加载模型
            async def load_models():
                global wan_pipeline, wav2vec_feature_extractor, audio_encoder

                # 初始化模型
                if wan_pipeline is None:
                    # 初始化模型
                    if config.PRELOAD_MODELS:
                        logger.info("Preloading models...")
                        await init_models()
                        logger.info("✓ Models loaded")
                    else:
                        logger.info("Model preloading disabled")

                return wan_pipeline, wav2vec_feature_extractor, audio_encoder

            self.pipeline, self.wav2vec_feature_extractor, self.audio_encoder = \
                await loop.run_in_executor(None, load_models)

            logger.info("视频生成模型加载成功")

        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise

    async def generate_video(
            self,
            prompt: str,
            image_path: str,
            audio_path: str,
            output_path: str,
            task_id: str
    ) -> bool:
        """生成视频"""
        try:
            logger.info(f"Task {task_id}: 开始生成视频")

            # 创建临时目录
            task_audio_dir = config.AUDIO_SAVE_DIR / task_id
            task_audio_dir.mkdir(parents=True, exist_ok=True)

            loop = asyncio.get_event_loop()

            def do_generation():
                try:
                    # 1. 处理音频
                    logger.info(f"Task {task_id}: 处理音频")
                    human_speech = audio_prepare_single(audio_path)

                    # 2. 获取音频嵌入
                    logger.info(f"Task {task_id}: 提取音频嵌入")
                    audio_embedding = get_embedding(
                        human_speech,
                        self.wav2vec_feature_extractor,
                        self.audio_encoder
                    )

                    # 保存音频嵌入
                    emb_path = task_audio_dir / '1.pt'
                    torch.save(audio_embedding, emb_path)

                    # 保存处理后的音频
                    sum_audio_path = task_audio_dir / 'sum.wav'
                    sf.write(str(sum_audio_path), human_speech, config.AUDIO_SAMPLE_RATE)

                    # 3. 准备输入数据
                    input_clip = {
                        'prompt': prompt,
                        'cond_video': image_path,
                        'cond_audio': {'person1': str(emb_path)},
                        'video_audio': str(sum_audio_path),
                        'audio_type': 'single'
                    }

                    # 4. 生成视频
                    logger.info(f"Task {task_id}: 开始视频生成")
                    gen_config = config.get_generation_config()

                    video_tensor = self.pipeline.generate_infinitetalk(
                        input_clip,
                        size_buckget=config.MODEL_SIZE,
                        **gen_config,
                        extra_args=None,
                    )

                    # 5. 保存视频
                    logger.info(f"Task {task_id}: 保存视频到 {output_path}")
                    output_dir = Path(output_path).parent
                    output_dir.mkdir(parents=True, exist_ok=True)

                    save_video_ffmpeg(
                        video_tensor,
                        str(Path(output_path).with_suffix('')),
                        [str(sum_audio_path)],
                        high_quality_save=config.HIGH_QUALITY_SAVE
                    )

                    logger.info(f"Task {task_id}: 视频生成完成")
                    return True

                except Exception as e:
                    logger.error(f"Task {task_id}: 生成过程出错: {e}")
                    import traceback
                    traceback.print_exc()
                    return False

            # 在线程池中执行整个生成过程
            success = await loop.run_in_executor(None, do_generation)

            return success

        except Exception as e:
            logger.error(f"Task {task_id}: 视频生成失败: {e}")
            import traceback
            traceback.print_exc()
            return False


video_engine = VideoEngine()


# ==================== 视频任务处理器 ====================
class VideoTaskWorker:
    def __init__(self):
        self.running = False
        self.task_queue = asyncio.Queue()

    async def start(self):
        """启动任务处理器"""
        self.running = True
        logger.info("视频任务处理器已启动")

        while self.running:
            try:
                task_id = await asyncio.wait_for(
                    self.task_queue.get(),
                    timeout=1.0
                )
                await self.process_task(task_id)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"任务处理器错误: {e}")

    async def stop(self):
        """停止任务处理器"""
        self.running = False
        logger.info("视频任务处理器已停止")

    async def add_task(self, task_id: str):
        """添加任务到队列"""
        await self.task_queue.put(task_id)
        logger.info(f"任务已加入队列: {task_id}")

    async def process_task(self, task_id: str):
        """处理单个任务"""
        try:
            task = await db_manager.get_task_by_id(task_id)
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return

            logger.info(f"开始处理任务: {task_id}")

            # 更新为处理中
            await db_manager.update_task_processing(task_id)

            # 生成输出路径
            now = datetime.now()
            date_dir = config.OUTPUT_VIDEO_DIR / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
            output_path = date_dir / f"{task_id}.mp4"

            # 执行视频生成
            success = await video_engine.generate_video(
                prompt=task.prompt,
                image_path=task.image_path,
                audio_path=task.audio_path,
                output_path=str(output_path),
                task_id=task_id
            )

            if success:
                video_download_url = f"/api/download/video/{output_path.relative_to(config.OUTPUT_VIDEO_DIR)}"
                await db_manager.update_task_completed(
                    task_id,
                    str(output_path),
                    video_download_url
                )
                logger.info(f"任务完成: {task_id}")
            else:
                await db_manager.update_task_failed(task_id, "视频生成失败")
                logger.error(f"任务失败: {task_id}")

        except Exception as e:
            error_msg = f"任务处理异常: {str(e)}"
            logger.error(f"{error_msg}, task_id: {task_id}")

            import traceback
            traceback.print_exc()

            await db_manager.update_task_failed(task_id, error_msg)


video_task_worker = VideoTaskWorker()
