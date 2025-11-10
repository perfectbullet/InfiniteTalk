"""Command execution helpers for InfiniteTalk generation."""

from datetime import datetime
from pathlib import Path
import subprocess

from ..core.config import LOG_FILE, PROJECT_ROOT, PYTHON_EXECUTABLE
from .task_manager import TaskManager


def run_infinitetalk_command(input_json: str, save_file: str, manager: TaskManager) -> None:
	"""Spawn the InfiniteTalk CLI with the FusioniX LoRA pipeline."""
	command = [
		PYTHON_EXECUTABLE,
		"generate_infinitetalk.py",
		"--ckpt_dir",
		"weights/Wan2.1-I2V-14B-480P",
		"--wav2vec_dir",
		"weights/chinese-wav2vec2-base",
		"--infinitetalk_dir",
		"weights/InfiniteTalk/single/infinitetalk.safetensors",
		"--lora_dir",
		"Wan14BT2VFusioniX/FusionX_LoRa/Wan2.1_I2V_14B_FusionX_LoRA.safetensors",
		"--input_json",
		input_json,
		"--lora_scale",
		"1.0",
		"--size",
		"infinitetalk-480",
		"--sample_text_guide_scale",
		"1.0",
		"--sample_audio_guide_scale",
		"2.0",
		"--sample_steps",
		"8",
		"--mode",
		"streaming",
		"--motion_frame",
		"9",
		"--sample_shift",
		"2",
		"--num_persistent_param_in_dit",
		"0",
		"--save_file",
		save_file,
	]

	log_path = Path(LOG_FILE)
	log_path.parent.mkdir(parents=True, exist_ok=True)

	start_time = datetime.utcnow().isoformat()
	try:
		with log_path.open("a", encoding="utf-8", errors="ignore") as log_file:
			log_file.write(
				f"\n[{start_time}] Starting InfiniteTalk job"
				f" input_json={input_json} save_file={save_file}\n"
			)
			log_file.flush()
			process = subprocess.Popen(
				command,
				cwd=PROJECT_ROOT,
				stdout=log_file,
				stderr=log_file,
			)
			return_code = process.wait()
			finish_time = datetime.utcnow().isoformat()
			status = "completed" if return_code == 0 else f"failed (code={return_code})"
			log_file.write(f"[{finish_time}] Job {status}\n")
	except Exception as exc:
		error_time = datetime.utcnow().isoformat()
		with log_path.open("a", encoding="utf-8", errors="ignore") as log_file:
			log_file.write(f"[{error_time}] Job crashed: {exc}\n")
		raise
	finally:
		manager.finish_task()
