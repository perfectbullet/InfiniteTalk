import subprocess
import logging
import time
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class GenerationStatus(Enum):
    """生成状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class InfiniteTalkGenerator:
    """InfiniteTalk 视频生成器（增强版 - 支持任务信息和进程管理）"""

    def __init__(self, timeout: Optional[int] = None):
        """
        Args:
            timeout: 超时时间（秒），None 表示不限制
        """
        self.script_path = "generate_infinitetalk.py"
        self.timeout = timeout
        self.status = GenerationStatus.IDLE

    def generate(
            self,
            task_info: Dict[str, Any],
            task_id: str,
            **kwargs
    ) -> Dict[str, Any]:
        """
        执行 InfiniteTalk 视频生成（非阻塞）

        Args:
            task_info: 任务信息字典，包含 prompt, image_path, audio_path
            task_id: 任务 ID
            **kwargs: 额外参数

        Returns:
            Dict: 包含 success, pid, log_path, json_path 等信息
        """
        try:
            # 创建 JSON 文件
            json_path = self._create_task_json(task_info, task_id)

            # 创建日志文件路径
            log_path = Path(f"{task_id}.log")

            # 构建命令
            cmd = self._build_command(json_path, task_id, **kwargs)

            # 构建 nohup 命令
            cmd_str = ' '.join(cmd)
            full_cmd = f"nohup {cmd_str} > {log_path} 2>&1 & echo $!"

            logger.info(f"Starting generation for task: {task_id}")
            logger.info(f"Command: {full_cmd}")

            # 使用 shell 执行 nohup 命令并获取 PID
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True
            )

            if result.returncode == 0 and result.stdout.strip():
                pid = int(result.stdout.strip())
                logger.info(f"✅ Generation started with PID: {pid}")

                return {
                    'success': True,
                    'pid': pid,
                    'log_path': str(log_path),
                    'json_path': str(json_path),
                    'status': 'running'
                }
            else:
                logger.error(f"Failed to start generation: {result.stderr}")
                return {
                    'success': False,
                    'error': f'Failed to start process: {result.stderr}'
                }

        except Exception as e:
            logger.error(f"Error during generation: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def _create_task_json(self, task_info: Dict[str, Any], task_id: str) -> Path:
        """
        创建任务 JSON 文件

        Args:
            task_info: 任务信息
            task_id: 任务 ID

        Returns:
            Path: JSON 文件路径
        """
        # 创建 JSON 内容，参考 single_example_zmh2.json 格式
        json_content = {
            "prompt": task_info.get('prompt', ''),
            "cond_video": task_info.get('image_path', ''),
            "cond_audio": {
                "person1": task_info.get('audio_path', '')
            }
        }

        # 保存 JSON 文件
        json_path = Path(f"task_{task_id}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_content, f, ensure_ascii=False, indent=4)

        logger.info(f"Created task JSON: {json_path}")
        return json_path

    def _build_command(self, json_path: Path, task_id: str, **kwargs) -> list:
        """构建命令行参数"""
        cmd = [
            "python", self.script_path,
            "--ckpt_dir", str(kwargs.get("ckpt_dir", "weights/Wan2.1-I2V-14B-480P")),
            "--wav2vec_dir", str(kwargs.get("wav2vec_dir", "weights/chinese-wav2vec2-base")),
            "--infinitetalk_dir",
            str(kwargs.get("infinitetalk_dir", "weights/InfiniteTalk/single/infinitetalk.safetensors")),
            "--input_json", str(json_path),
            "--size", kwargs.get("size", "infinitetalk-480"),
            "--sample_steps", str(kwargs.get("sample_steps", 40)),
            "--mode", kwargs.get("mode", "streaming"),
            "--quant", kwargs.get("quant", "fp8"),
            "--quant_dir",
            str(kwargs.get("quant_dir", "weights/InfiniteTalk/quant_models/infinitetalk_single_fp8.safetensors")),
            "--motion_frame", str(kwargs.get("motion_frame", 9)),
            "--num_persistent_param_in_dit", str(kwargs.get("num_persistent_param_in_dit", 0)),
            "--save_file", f"infinitetalk_res_{task_id}",
        ]

        return cmd

    def get_status(self, pid: int) -> str:
        """
        获取进程状态

        Args:
            pid: 进程 ID

        Returns:
            str: 状态 (running, completed, failed)
        """
        try:
            # 检查进程是否存在
            result = subprocess.run(
                ['ps', '-p', str(pid)],
                capture_output=True
            )

            if result.returncode == 0:
                return 'running'
            else:
                return 'completed'
        except Exception as e:
            logger.error(f"Error checking process status: {e}")
            return 'failed'

    def cancel(self, pid: int, force: bool = False) -> bool:
        """
        取消指定 PID 的生成任务

        Args:
            pid: 进程 ID
            force: 是否强制终止

        Returns:
            bool: 是否成功取消
        """
        try:
            import signal

            if force:
                logger.warning(f"Forcefully killing process {pid}...")
                subprocess.run(['kill', '-9', str(pid)])
            else:
                logger.info(f"Terminating process {pid} gracefully...")
                subprocess.run(['kill', '-15', str(pid)])

            return True
        except Exception as e:
            logger.error(f"Error cancelling process {pid}: {e}")
            return False