import subprocess
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from api_server.config import config

logger = logging.getLogger(__name__)


class InfiniteTalkGenerator:
    """InfiniteTalk 视频生成器（最佳实践版本）"""

    def __init__(self, timeout: Optional[int] = None):
        """
        Args:
            timeout: 超时时间（秒），None 表示不限制
        """
        self.script_path = "generate_infinitetalk.py"
        self.timeout = timeout
        self.active_processes = {}  # 保存活跃进程 {task_id: process_info}

    def generate(
            self,
            task_info: Dict[str, Any],
            task_id: str,
            **kwargs
    ) -> Dict[str, Any]:
        """
        执行 InfiniteTalk 视频生成（非阻塞，最佳实践）

        Args:
            task_info: 任务信息字典，包含 prompt, image_path, audio_path
            task_id: 任务 ID
            **kwargs: 额外参数
                - ckpt_dir: 模型权重目录
                - wav2vec_dir: wav2vec 权重目录
                - infinitetalk_dir: InfiniteTalk 权重目录
                - size: 尺寸 (默认: infinitetalk-480)
                - sample_steps: 采样步数 (默认: 40)
                - mode: 模式 (默认: streaming)
                - quant: 量化类型 (默认: fp8)
                - quant_dir: 量化模型目录
                - motion_frame: 运动帧数 (默认: 9)
                - num_persistent_param_in_dit: 持久化参数数量 (默认: 0)

        Returns:
            Dict: 包含 success, pid, log_path, json_path 等信息
            成功时: {
                'success': True,
                'pid': int,           # 真正的 Python 进程 PID
                'log_path': str,      # 日志文件路径
                'json_path': str,     # 任务 JSON 文件路径
                'status': 'running',
                'started_at': str,    # ISO 格式时间戳
                'command': list       # 执行的命令
            }
            失败时: {
                'success': False,
                'error': str          # 错误信息
            }
        """
        try:
            # 1️⃣ 创建任务 JSON 文件
            json_path = self._create_task_json(task_info, task_id)

            # 2️⃣ 创建日志文件路径
            log_dir = config.LOG_DIR
            log_dir.mkdir(exist_ok=True)
            log_path = log_dir / f"task_{task_id}.log"
            generate_video_file = config.OUTPUT_VIDEO_DIR / f"infinitetalk_res_{task_id}.mp4"
            # 3️⃣ 构建命令（列表形式，不使用 shell）
            cmd = self._build_command(json_path, generate_video_file, **kwargs)

            logger.info(f"🚀 启动视频生成任务: {task_id}")
            logger.info(f"📝 命令: {' '.join(str(c) for c in cmd)}")
            logger.info(f"📂 日志文件: {log_path}")
            logger.info(f"📄 配置文件: {json_path}")

            # 4️⃣ 打开日志文件（行缓冲模式，实时写入）
            log_file = open(log_path, 'w', buffering=1, encoding='utf-8')

            # 5️⃣ 启动进程（不使用 shell，直接启动 Python）
            process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,  # 创建新会话，父进程退出不影响子进程
                cwd=Path(self.script_path).parent or None  # 设置工作目录
            )

            # 6️⃣ 获取真正的 PID
            real_pid = process.pid

            logger.info(f"✅ 进程已启动: PID={real_pid}")

            # 7️⃣ 保存进程信息（用于后续管理）
            process_info = {
                'process': process,
                'log_file': log_file,
                'log_path': str(log_path),
                'json_path': str(json_path),
                'started_at': datetime.now(),
                'task_info': task_info,
                'generate_video_file': generate_video_file
            }
            self.active_processes[task_id] = process_info

            # 8️⃣ 返回结果
            return {
                'success': True,
                'pid': real_pid,
                'log_path': str(log_path),
                'json_path': str(json_path),
                'status': 'running',
                'started_at': datetime.now().isoformat(),
                'command': [str(c) for c in cmd],
                'generate_video_file': generate_video_file
            }

        except FileNotFoundError as e:
            error_msg = f"脚本文件不存在: {self.script_path}"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'details': str(e)
            }

        except PermissionError as e:
            error_msg = f"权限不足，无法执行脚本或写入日志"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'details': str(e)
            }

        except Exception as e:
            error_msg = f"启动视频生成失败: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }

    def _create_task_json(self, task_info: Dict[str, Any], task_id: str) -> Path:
        """
        创建任务 JSON 配置文件

        Args:
            task_info: 任务信息，包含 prompt, image_path, audio_path
            task_id: 任务 ID

        Returns:
            Path: JSON 文件路径
        """
        # 创建配置目录
        config_dir = Path("configs")
        config_dir.mkdir(exist_ok=True)

        # 构建 JSON 内容（参考 single_example_zmh2.json 格式）
        json_content = {
            "prompt": task_info.get('prompt', ''),
            "cond_video": task_info.get('image_path', ''),
            "cond_audio": {
                "person1": task_info.get('audio_path', '')
            }
        }

        # 保存到文件
        json_path = config_dir / f"task_{task_id}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_content, f, ensure_ascii=False, indent=4)

        logger.info(f"📝 创建任务配置文件: {json_path}")
        return json_path

    def _build_command(self, json_path: Path, save_file, **kwargs) -> list:
        """
        构建命令行参数列表

        Args:
            json_path: JSON 配置文件路径
            task_id: 任务 ID
            **kwargs: 可选参数

        Returns:
            list: 命令行参数列表
        """
        cmd = [
            "python",
            str(self.script_path),
            "--ckpt_dir",
            str(kwargs.get("ckpt_dir", "weights/Wan2.1-I2V-14B-480P")),
            "--wav2vec_dir",
            str(kwargs.get("wav2vec_dir", "weights/chinese-wav2vec2-base")),
            "--infinitetalk_dir",
            str(kwargs.get("infinitetalk_dir", "weights/InfiniteTalk/single/infinitetalk.safetensors")),
            "--input_json",
            str(json_path),
            "--size",
            kwargs.get("size", "infinitetalk-480"),
            "--sample_steps",
            str(kwargs.get("sample_steps", 40)),
            "--mode",
            kwargs.get("mode", "streaming"),
            "--quant",
            kwargs.get("quant", "fp8"),
            "--quant_dir",
            str(kwargs.get("quant_dir", "weights/InfiniteTalk/quant_models/infinitetalk_single_fp8.safetensors")),
            "--motion_frame",
            str(kwargs.get("motion_frame", 9)),
            "--num_persistent_param_in_dit",
            str(kwargs.get("num_persistent_param_in_dit", 0)),
            "--save_file",
            save_file,
        ]

        return cmd

    def get_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态（结合进程返回码和日志内容判断）

        Returns:
            Dict: {
                'status': 'running' | 'success' | 'failed' | 'not_found' | 'error',
                'pid': int or None,
                'uptime': float or None,
                'return_code': int or None,
                'log_path': str or None,
                'error_message': str or None  # 失败时的错误信息
            }
        """
        if task_id not in self.active_processes:
            return {
                'status': 'not_found',
                'pid': None,
                'uptime': None,
                'return_code': None,
                'log_path': None,
                'error_message': None
            }

        process_info = self.active_processes[task_id]
        process = process_info['process']
        log_path = process_info['log_path']

        try:
            # 检查进程是否还在运行
            return_code = process.poll()
            uptime = (datetime.now() - process_info['started_at']).total_seconds()

            if return_code is None:
                # 进程还在运行
                return {
                    'status': 'running',
                    'pid': process.pid,
                    'uptime': uptime,
                    'return_code': None,
                    'log_path': log_path,
                    'error_message': None
                }
            else:
                # 进程已结束，分析日志确定状态
                status, error_message = self._analyze_log_status(log_path, return_code)

                return {
                    'status': status,
                    'pid': process.pid,
                    'uptime': uptime,
                    'return_code': return_code,
                    'log_path': log_path,
                    'error_message': error_message
                }

        except Exception as e:
            logger.error(f"检查进程状态失败: {e}")
            return {
                'status': 'error',
                'pid': process.pid if process else None,
                'uptime': None,
                'return_code': None,
                'log_path': log_path,
                'error_message': str(e)
            }

    def _analyze_log_status(self, log_path: str, return_code: int) -> tuple[str, Optional[str]]:
        """
        分析日志文件确定任务状态

        Args:
            log_path: 日志文件路径
            return_code: 进程返回码

        Returns:
            tuple: (status, error_message)
                status: 'success' | 'failed'
                error_message: 错误信息（如果失败）
        """
        try:
            # 读取日志文件最后几行
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                # 读取全部内容（对于小文件）或最后 100 行
                lines = f.readlines()
                last_lines = lines[-100:] if len(lines) > 100 else lines
                log_content = ''.join(last_lines)

            # 定义成功标志（根据你的实际日志调整）
            success_markers = [
                'Generation finished.Saving generated video to',
            ]

            # 定义失败标志
            error_markers = [
                'Error:',
                'Exception:',
                'Traceback',
                'CUDA out of memory',
                'RuntimeError',
                'AssertionError',
                'ValueError',
                'KeyError',
                'FileNotFoundError',
                '❌'
            ]

            # 检查成功标志
            if any(marker in log_content for marker in success_markers):
                return 'success', None

            # 检查失败标志
            for marker in error_markers:
                if marker in log_content:
                    # 提取错误信息（简化版）
                    error_lines = [line.strip() for line in last_lines
                                   if marker.lower() in line.lower()]
                    error_message = error_lines[0] if error_lines else f"Found error marker: {marker}"
                    return 'failed', error_message

            # 根据返回码判断
            if return_code == 0:
                return 'success', None
            else:
                # 尝试从日志末尾提取错误信息
                error_message = '\n'.join(last_lines[-5:]).strip()
                return 'failed', error_message or f"Process exited with code {return_code}"

        except FileNotFoundError:
            logger.warning(f"日志文件不存在: {log_path}")
            return ('failed', 'Log file not found') if return_code != 0 else ('success', None)

        except Exception as e:
            logger.error(f"分析日志失败: {e}")
            return ('failed', str(e)) if return_code != 0 else ('success', None)

    def cancel(self, task_id: str, force: bool = False) -> Dict[str, Any]:
        """
        取消指定任务

        Args:
            task_id: 任务 ID
            force: 是否强制终止（SIGKILL）

        Returns:
            Dict: {
                'success': bool,
                'message': str,
                'pid': int or None
            }
        """
        if task_id not in self.active_processes:
            return {
                'success': False,
                'message': f'任务 {task_id} 不存在或未运行',
                'pid': None
            }

        process_info = self.active_processes[task_id]
        process = process_info['process']
        pid = process.pid

        try:
            if force:
                logger.warning(f"🔴 强制终止任务: {task_id} (PID={pid})")
                process.kill()  # SIGKILL
                message = f'任务 {task_id} 已强制终止'
            else:
                logger.info(f"🟡 优雅终止任务: {task_id} (PID={pid})")
                process.terminate()  # SIGTERM
                message = f'任务 {task_id} 已发送终止信号'

            # 等待进程结束（最多 5 秒）
            try:
                process.wait(timeout=5)
                logger.info(f"✅ 任务 {task_id} 已停止")
            except subprocess.TimeoutExpired:
                if not force:
                    logger.warning(f"⚠️ 任务 {task_id} 未响应终止信号，强制终止")
                    process.kill()
                    process.wait(timeout=2)

            # 关闭日志文件
            if 'log_file' in process_info and process_info['log_file']:
                try:
                    process_info['log_file'].close()
                except:
                    pass

            # 移除进程信息
            del self.active_processes[task_id]

            return {
                'success': True,
                'message': message,
                'pid': pid
            }

        except Exception as e:
            error_msg = f'终止任务失败: {str(e)}'
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                'success': False,
                'message': error_msg,
                'pid': pid
            }

    def cleanup(self):
        """清理所有活跃进程（通常在程序退出时调用）"""
        logger.info(f"🧹 清理 {len(self.active_processes)} 个活跃进程...")

        for task_id in list(self.active_processes.keys()):
            try:
                self.cancel(task_id, force=True)
            except Exception as e:
                logger.error(f"清理任务 {task_id} 失败: {e}")

        logger.info("✅ 清理完成")

    def get_active_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有活跃任务

        Returns:
            Dict: {task_id: task_info}
        """
        active_tasks = {}

        for task_id, process_info in self.active_processes.items():
            status = self.get_status(task_id)
            active_tasks[task_id] = {
                'task_id': task_id,
                'pid': process_info['process'].pid,
                'status': status['status'],
                'started_at': process_info['started_at'].isoformat(),
                'uptime': status.get('uptime'),
                'log_path': process_info['log_path'],
                'json_path': process_info['json_path']
            }

        return active_tasks