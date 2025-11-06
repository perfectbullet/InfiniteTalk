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
            logger.info(f"开始处理任务: {task_id}")
            task = await db_manager.get_task_by_id(task_id)
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return
            # 第一次更新
            started_at = datetime.now()
            logger.info(f"📍 [步骤1] 准备第一次更新为 processing")
            try:
                await db_manager.update_task_status(
                    task_id,
                    'processing',
                    started_at=started_at,
                )
                logger.info(f"📍 [步骤1完成] 第一次更新完成")
            except Exception as e:
                logger.error(f"📍 [步骤1失败] {e}", exc_info=True)
                raise
            # 准备任务信息
            task_info = {
                'prompt': task.prompt,
                'image_path': task.image_path,
                'audio_path': task.audio_path
            }
            # 执行视频生成
            logger.info(f"📍 [步骤2] 准备执行视频生成")
            result = self.generator.generate(task_info, task_id)
            logger.info(f"📍 [步骤2完成] result: {result}")
            if result['success']:
                logger.info(f"📍 [步骤3] 准备第二次更新为 running, PID={result['pid']}")
                try:
                    await db_manager.update_task_status(
                        task_id,
                        'running',
                        pid=result['pid'],
                        started_at=started_at,
                        log_path=result['log_path'],
                        command=result['command'],
                        generate_video_file=result['generate_video_file']
                    )
                    logger.info(f"📍 [步骤3完成] 第二次更新完成")
                except Exception as e:
                    logger.error(f"📍 [步骤3失败] {e}", exc_info=True)
                    logger.exception(e)
                    raise e
                logger.info(f"任务已启动: {task_id}, PID: {result['pid']}")
                # 启动监控
                logger.info(f"📍 [步骤4] 启动监控任务")
                asyncio.create_task(self.monitor_task(task_id, result['pid'], result['generate_video_file']))
                logger.info(f"📍 [步骤4完成] 监控任务已启动")
            else:
                ended_at = datetime.now()
                logger.error(f"视频生成失败: {result.get('error')}")
                await db_manager.update_task_status(
                    task_id,
                    status='failed',
                    error_message=result.get('error', '视频生成启动失败'),
                    ended_at=ended_at
                )
        except Exception as e:
            error_msg = f"任务处理异常: {str(e)}"
            logger.error(f"{error_msg}, task_id: {task_id}", exc_info=True)
            ended_at = datetime.now()
            try:
                await db_manager.update_task_status(
                    task_id,
                    status='failed',
                    error_message=error_msg,
                    ended_at=ended_at
                )
            except Exception as update_error:
                logger.error(f"更新失败状态时出错: {update_error}", exc_info=True)

    async def monitor_task(self, task_id: str, pid: int, generate_video_file: str):
        """
        监控任务执行状态
        Args:
            task_id: 任务 ID
            pid: 进程 ID
            generate_video_file:
        """
        logger.info(f"开始监控任务: {task_id}, PID: {pid}")
        while True:
            try:
                await asyncio.sleep(5)  # 每 5 秒检查一次
                # 检查进程状态（非阻塞）
                status = self.generator.get_status(task_id)
                if status["status"] == "running":
                    # 运行中更新运行时长
                    await db_manager.update_task_status(
                        task_id,
                        status=status["status"],
                        uptime=status['uptime'],
                    )
                elif status['status'] == 'success':
                    # 进程已完成，检查输出文件
                    video_path = Path(generate_video_file)
                    if video_path.exists():
                        ended_at = datetime.now()
                        await db_manager.update_task_status(
                            task_id,
                            status='success',
                            video_path=str(video_path),
                            ended_at=ended_at,
                            uptime=status['uptime'],
                        )
                        logger.info(f"任务完成: {task_id}")
                    else:
                        # 文件不存在，任务失败
                        ended_at = datetime.now()
                        await db_manager.update_task_status(
                            task_id,
                            status='failed',
                            error_message='输出视频文件不存在',
                            ended_at=ended_at,
                        )
                        logger.error(f"任务失败（文件不存在）: {task_id}")
                    break
                elif status['status'] == 'failed':
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
                raise e

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
