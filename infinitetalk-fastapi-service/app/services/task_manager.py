"""Simple concurrency limiter for generation tasks."""

from threading import Lock
from typing import Optional

from ..core.config import MAX_CONCURRENT_TASKS


class TaskManager:
	"""Track the number of active generation jobs."""

	def __init__(self, max_tasks: Optional[int] = None) -> None:
		self.max_tasks = max_tasks or MAX_CONCURRENT_TASKS
		self._running_tasks = 0
		self._lock = Lock()

	def try_start(self) -> bool:
		"""Attempt to reserve a task slot."""
		with self._lock:
			if self._running_tasks >= self.max_tasks:
				return False
			self._running_tasks += 1
			return True

	def finish_task(self) -> None:
		"""Release a task slot after completion."""
		with self._lock:
			if self._running_tasks:
				self._running_tasks -= 1

	@property
	def running(self) -> int:
		with self._lock:
			return self._running_tasks


task_manager = TaskManager()
