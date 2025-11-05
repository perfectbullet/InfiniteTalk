import asyncio
from datetime import datetime
from pathlib import Path

from api_server.InfiniteTalkGenerator import InfiniteTalkGenerator
from api_server.api_loger import logger
from api_server.database import db_manager


# ==================== 视频任务处理器 ====================
class VideoTaskWorker:
    def __init__(self):
        self.running = False
        self.task_queue = asyncio.Queue()
        self.generator = InfiniteTalkGenerator(timeout=3600)

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

            # 更新为处理中，记录开始时间
            started_at = datetime.now()
            await db_manager.update_task_status(
                task_id,
                status='processing',
                started_at=started_at
            )

            # 准备任务信息
            task_info = {
                'prompt': task.prompt,
                'image_path': task.image_path,
                'audio_path': task.audio_path
            }

            # 执行视频生成（非阻塞，直接调用）
            result = self.generator.generate(task_info, task_id)

            if result['success']:
                # 更新任务信息，包含 PID
                await db_manager.update_task_status(
                    task_id,
                    status='running',
                    pid=result['pid'],
                    started_at=started_at
                )

                logger.info(f"任务已启动: {task_id}, PID: {result['pid']}")

                # 启动监控任务
                asyncio.create_task(self.monitor_task(task_id, result['pid']))
            else:
                ended_at = datetime.now()
                await db_manager.update_task_status(
                    task_id,
                    status='failed',
                    error_message=result.get('error', '视频生成启动失败'),
                    ended_at=ended_at
                )
                logger.error(f"任务启动失败: {task_id}")

        except Exception as e:
            error_msg = f"任务处理异常: {str(e)}"
            logger.error(f"{error_msg}, task_id: {task_id}")

            import traceback
            traceback.print_exc()

            ended_at = datetime.now()
            await db_manager.update_task_status(
                task_id,
                status='failed',
                error_message=error_msg,
                ended_at=ended_at
            )

    async def monitor_task(self, task_id: str, pid: int):
        """
        监控任务执行状态

        Args:
            task_id: 任务 ID
            pid: 进程 ID
        """
        logger.info(f"开始监控任务: {task_id}, PID: {pid}")

        while True:
            try:
                await asyncio.sleep(10)  # 每 10 秒检查一次

                # 检查进程状态（非阻塞）
                status = self.generator.get_status(pid)

                if status == 'completed':
                    # 进程已完成，检查输出文件
                    video_path = Path(f"infinitetalk_res_{task_id}.mp4")

                    if video_path.exists():
                        # 生成输出路径
                        now = datetime.now()
                        from config import config
                        date_dir = config.OUTPUT_VIDEO_DIR / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
                        date_dir.mkdir(parents=True, exist_ok=True)

                        output_path = date_dir / f"{task_id}.mp4"

                        # 移动文件
                        import shutil
                        shutil.move(str(video_path), str(output_path))

                        video_download_url = f"/api/download/video/{output_path.relative_to(config.OUTPUT_VIDEO_DIR)}"

                        ended_at = datetime.now()
                        await db_manager.update_task_status(
                            task_id,
                            status='completed',
                            video_path=str(output_path),
                            video_url=video_download_url,
                            ended_at=ended_at
                        )

                        logger.info(f"任务完成: {task_id}")
                    else:
                        # 文件不存在，任务失败
                        ended_at = datetime.now()
                        await db_manager.update_task_status(
                            task_id,
                            status='failed',
                            error_message='输出视频文件不存在',
                            ended_at=ended_at
                        )
                        logger.error(f"任务失败（文件不存在）: {task_id}")

                    break

                elif status == 'failed':
                    ended_at = datetime.now()
                    await db_manager.update_task_status(
                        task_id,
                        status='failed',
                        error_message='进程异常退出',
                        ended_at=ended_at
                    )
                    logger.error(f"任务失败: {task_id}")
                    break

            except Exception as e:
                logger.error(f"监控任务异常: {task_id}, {e}")
                break

    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务 ID

        Returns:
            bool: 是否成功取消
        """
        try:
            task = await db_manager.get_task_by_id(task_id)
            if not task or not task.pid:
                logger.error(f"无法取消任务: {task_id}")
                return False

            # 取消进程（非阻塞）
            success = self.generator.cancel(task.pid, False)

            if success:
                ended_at = datetime.now()
                await db_manager.update_task_status(
                    task_id,
                    status='cancelled',
                    ended_at=ended_at
                )
                logger.info(f"任务已取消: {task_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"取消任务失败: {task_id}, {e}")
            return False

video_task_worker = VideoTaskWorker()
