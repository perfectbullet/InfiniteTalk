"""API route definitions."""

import mimetypes
import os

from fastapi import APIRouter, BackgroundTasks
from fastapi import HTTPException
from fastapi.responses import FileResponse
from loguru import logger

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


UPLOAD_IMAGE_DIR = '../output_videos/'


@router.get("/download/video/{filename}")
async def download_file(filename: str):
    """下载文件（支持正确的 MIME 类型和文件名）"""
    try:
        #  根据文件类型确定路径和默认 MIME 类型
        file_config = {
            "video": {
                "dir": UPLOAD_IMAGE_DIR,
                "default_media_type": "video/mp4"
            }
        }
        #   构建文件路径
        file_path = UPLOAD_IMAGE_DIR + filename
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {filename}"
            )
        #   自动检测 MIME 类型（优先使用文件扩展名）
        media_type, _ = mimetypes.guess_type(str(file_path))
        # 如果检测失败，使用默认值
        if media_type is None:
            media_type = file_config['video']["default_media_type"]
        # 返回文件响应（带正确的 MIME 类型和下载文件名）
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename  # ✅ 设置下载时的文件名
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/course/{ppt_name}")
async def get_course_data(ppt_name: str) -> dict:
    """获取课程数据（目前为硬编码数据）"""
    # 硬编码的课程数据
    course_data = [
        {
            "id": 1,
            "title": "第一讲:M09个性化首饰设计及制作",
            "slideContent": '<img src="slides/slide_001.png" style="max-width: 100%; height: auto;" alt="课程介绍">',
            "videoUrl": "http://192.168.8.231:50008/download/video/infinitetalk_res_480p_optimized_slide1v6.mp4",
            "duration": "0:10",
            "narration": "欢迎同学们选修制造工程体验课程M09：个性化首饰设计及制作。在这门课程中，你将学习首饰设计的基本原理，掌握3D建模和加工制作技能，亲手打造属于自己的独特作品。"
        },
        {
            "id": 2,
            "title": "第二讲:中心简介-历史沿革",
            "slideContent": '<img src="slides/slide_002.png" style="max-width: 100%; height: auto;" alt="历史沿革">',
            "videoUrl": "http://192.168.8.231:50008/download/video/infinitetalk_res_480p_optimized_slide3v2-rmb.webm",
            "duration": "0:10",
            "narration": "工训训练中心有着百年传承。从1921年的手工教学到金工实习，再到工训文化和工创理念，中心不断发展演进。如今，我们已经完成了从机械化、电气化到信息化、智能化的转型升级，始终走在工程教育创新的前沿。"
        },
        {
            "id": 3,
            "title": "第三讲:中心简介-功能定位",
            "slideContent": '<img src="slides/slide_003.png" style="max-width: 100%; height: auto;" alt="功能定位">',
            "videoUrl": "http://192.168.8.231:50008/download/video/infinitetalk_res_480p_optimized_slide3v4.mp4",
            "duration": "0:10",
            "narration": "清华大学基础工业训练中心，简称工训训练中心，是国际领先的工程实践与创新教育中心。中心传承工匠精神，弘扬创客文化，致力于培养学生的工程能力、劳动素质和创新创业能力，为同学们的梦想实现提供全方位支持。"
        }
    ]

    logger.info(f"Fetching course data for PPT: {ppt_name}")

    # 返回课程数据（后续可根据 ppt_name 从数据库查询）
    return {
        "pptName": ppt_name,
        "courses": course_data
    }
