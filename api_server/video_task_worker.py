import asyncio
from datetime import datetime
from pathlib import Path

from api_server.InfiniteTalkGenerator import InfiniteTalkGenerator
from api_server.api_loger import logger
from api_server.database import db_manager
from api_server.utils import convert_video_no_background


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
                # 步骤1: 检查数据库中是否有正在运行的任务
                running_tasks = await db_manager.get_tasks_by_status('running')

                if running_tasks:
                    # 有运行中的任务，检查并更新状态
                    task_id = running_tasks[0]['id']
                    logger.info(f"检测到运行中的任务: {task_id}")

                    status = self.generator.get_status_by_pid(running_tasks[0]['pid'])
                    logger.info(f"检测到运行中的任务: {status}")
                    if status["status"] == "running":
                        # 仍在运行，更新运行时长
                        await db_manager.update_task_status(
                            task_id,
                            status=status["status"],
                            uptime=status['uptime'],
                        )
                        logger.debug(f"任务运行中: {task_id}, 运行时长: {status['uptime']}s")

                    elif status['status'] == 'success':
                        # 任务成功完成 - 等待 monitor_task() 处理绿幕转换和最终状态更新
                        logger.info(f"检测到任务进程完成: {task_id}，等待 monitor_task 完成绿幕转换和最终更新")
                    else:
                        # 任务失败
                        ended_at = datetime.now()
                        await db_manager.update_task_status(
                            task_id,
                            status='failed',
                            error_message='进程异常退出: status: {}'.format(status),
                            ended_at=ended_at
                        )
                        logger.error(f"任务失败: {task_id}")

                    # 等待一段时间后继续检查
                    await asyncio.sleep(5.0)
                    continue

                # 步骤2: 没有运行中的任务，从队列获取新任务
                if self.task_queue.empty():
                    # 队列为空，短暂等待
                    await asyncio.sleep(1.0)
                    continue

                # 从队列获取任务
                task_id = await self.task_queue.get()
                logger.info(f"从队列获取任务: {task_id}")

                # 步骤3: 执行新任务
                await self.process_task(task_id)

            except Exception as e:
                logger.error(f"任务处理器错误: {e}", exc_info=True)
                await asyncio.sleep(1.0)

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
            logger.info("[步骤1] 准备第一次更新为 processing")
            try:
                await db_manager.update_task_status(
                    task_id,
                    'processing',
                    started_at=started_at,
                )
                logger.info("[步骤1完成] 第一次更新完成")
            except Exception as e:
                logger.error(f"[步骤1失败] {e}", exc_info=True)
                raise
            # 准备任务信息
            task_info = {
                'prompt': task.prompt,
                'image_path': task.image_path,
                'audio_path': task.audio_path
            }
            # 执行视频生成
            logger.info("[步骤2] 准备执行视频生成")
            result = self.generator.generate(task_info, task_id)
            logger.info(f"[步骤2完成] result: {result}")
            if result['success']:
                logger.info(f"[步骤3] 准备第二次更新为 running, PID={result['pid']}")
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
                    logger.info("[步骤3完成] 第二次更新完成")
                except Exception as e:
                    logger.error(f"[步骤3失败] {e}", exc_info=True)
                    logger.exception(e)
                    raise e
                logger.info(f"任务已启动: {task_id}, PID: {result['pid']}")
                # 启动监控
                logger.info("[步骤4] 启动监控任务")
                asyncio.create_task(self.monitor_task(task_id, result['pid'], result['generate_video_file']))
                logger.info("[步骤4完成] 监控任务已启动")
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
                video_path = Path(generate_video_file)
                if status["status"] == "running":
                    # 运行中更新运行时长
                    await db_manager.update_task_status(
                        task_id,
                        status=status["status"],
                        uptime=status['uptime'],
                        video_path=str(video_path)
                    )
                elif status['status'] == 'success':
                    # 进程已完成，检查输出文件
                    video_path = Path(generate_video_file)
                    if video_path.exists():
                        ended_at = datetime.now()
                        
                        # 调用绿幕转换服务
                        logger.info(f"开始绿幕转换处理: {video_path}")
                        no_bg_video_path = await convert_video_no_background(
                            str(video_path),
                            output_format=".webm",
                            similarity=0.35,
                            blend=0.1,
                            despill_mix=0.9,
                            despill_expand=0.1
                        )
                        
                        if no_bg_video_path:
                            logger.info(f"绿幕转换成功: {no_bg_video_path}")
                        else:
                            logger.warning(f"绿幕转换失败，继续使用原视频: {video_path}")
                        
                        # 绿幕转换完成，立即更新任务状态
                        logger.info("绿幕转换完成，准备立即更新任务状态为成功")
                        await asyncio.sleep(120)  # 确保前面的日志先输出

                        await db_manager.update_task_status(
                            task_id,
                            status='success',
                            video_path=str(video_path),
                            ended_at=ended_at,
                            uptime=status['uptime'],
                            no_bg_video_path=no_bg_video_path,
                            mov_video_path=no_bg_video_path.replace('.webm', '.mov') if no_bg_video_path else None
                        )
                        logger.info(f"任务完成: {task_id}")
                    else:
                        # 文件不存在，任务失败
                        ended_at = datetime.now()
                        await db_manager.update_task_status(
                            task_id,
                            status='failed',
                            error_message='输出视频文件不存在',
                            video_path=str(video_path),
                            ended_at=ended_at,
                        )
                        logger.error(f"任务失败（文件不存在）: {task_id}")
                    break
                elif status['status'] == 'failed':
                    ended_at = datetime.now()
                    await db_manager.update_task_status(
                        task_id,
                        status='failed',
                        video_path=str(video_path),
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
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return False
            
            # 检查任务是否有 PID（是否已启动）
            if not task.pid:
                logger.warning(f"任务 {task_id} 未启动或未记录 PID，直接标记为已取消")
                ended_at = datetime.now()
                await db_manager.update_task_status(
                    task_id,
                    status='cancelled',
                    ended_at=ended_at
                )
                return True

            # 调用 generator 的 cancel 方法杀死进程
            result = self.generator.cancel(task_id, force=False)

            if result['success']:
                ended_at = datetime.now()
                await db_manager.update_task_status(
                    task_id,
                    status='cancelled',
                    ended_at=ended_at
                )
                logger.info(f"任务已取消: {task_id}, PID: {result['pid']}")
                return True
            else:
                logger.error(f"取消任务失败: {result['message']}")
                return False

        except Exception as e:
            logger.error(f"取消任务失败: {task_id}, {e}", exc_info=True)
            return False

video_task_worker = VideoTaskWorker()
