"""API route definitions."""

from fastapi import APIRouter, BackgroundTasks, HTTPException

from ..core.logging import get_log_content
from ..models.schemas import GenerateRequest
from ..services.command_executor import run_infinitetalk_command
from ..services.task_manager import task_manager


router = APIRouter()


@router.post("/generate")
async def generate_video(request: GenerateRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
	if not task_manager.try_start():
		raise HTTPException(status_code=429, detail="Only one task can run at a time.")
	try:
		background_tasks.add_task(
			run_infinitetalk_command,
			request.input_json,
			request.save_file,
			task_manager,
		)
	except Exception:
		task_manager.finish_task()
		raise
	return {"status": "started"}


@router.get("/logs")
async def read_logs() -> dict[str, str]:
	return {"logs": get_log_content()}
