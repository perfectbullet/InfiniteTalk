"""Core configuration for the InfiniteTalk FastAPI service."""

from pathlib import Path
import sys


SERVICE_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

LOG_DIR = SERVICE_ROOT / "logs"
LOG_FILE = LOG_DIR / "execution.log"

PYTHON_EXECUTABLE = sys.executable

# Limit concurrent generation tasks to align with GPU resource constraints.
MAX_CONCURRENT_TASKS = 1


def ensure_directories() -> None:
	"""Make sure required directories exist before runtime."""
	LOG_DIR.mkdir(parents=True, exist_ok=True)


ensure_directories()
