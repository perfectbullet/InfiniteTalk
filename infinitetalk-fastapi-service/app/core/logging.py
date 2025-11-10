"""Utility helpers for accessing service logs."""

from pathlib import Path

from .config import LOG_FILE


def get_log_content(limit: int = 5000) -> str:
	"""Return the tail of the execution log for quick inspection."""
	log_path = Path(LOG_FILE)
	if not log_path.exists():
		return ""
	data = log_path.read_text(encoding="utf-8", errors="ignore")
	if len(data) <= limit:
		return data
	return data[-limit:]
