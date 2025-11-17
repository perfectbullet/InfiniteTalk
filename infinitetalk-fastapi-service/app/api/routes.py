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


UPLOAD_VIDEO_DIR = '../output_videos/'


@router.get("/download/video/{filename}")
async def download_file(filename: str):
    """下载文件（支持正确的 MIME 类型和文件名）"""
    try:
        #  根据文件类型确定路径和默认 MIME 类型
        file_config = {
            "video": {
                "dir": UPLOAD_VIDEO_DIR,
                "default_media_type": "video/mp4"
            }
        }
        #   构建文件路径
        file_path = UPLOAD_VIDEO_DIR + filename
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
            filename=filename
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

UPLOAD_IMAGE_DIR = '../show_demo2/slides'

@router.get("/download/image/{filename}")
async def download_image(filename: str):
    """下载文件（支持正确的 MIME 类型和文件名）"""
    try:
        #   构建文件路径
        file_path = os.path.normpath(os.path.join(UPLOAD_IMAGE_DIR, filename))
        if not os.path.abspath(file_path).startswith(os.path.abspath(UPLOAD_IMAGE_DIR)):
            raise HTTPException(status_code=400, detail="Invalid file path")

        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {filename}"
            )
        #   自动检测 MIME 类型（优先使用文件扩展名）
        media_type, _ = mimetypes.guess_type(file_path)
        # 如果检测失败，使用默认值
        if media_type is None:
            raise HTTPException(
                status_code=404,
                detail=f"File type not found: {filename}"
            )
        # 返回文件响应（带正确的 MIME 类型和下载文件名）
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename
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
            "videoUrl": ['http://192.168.8.231:50008/download/video/infinitetalk_res_480p_greenbg_slide1v9_rmb1.webm'],
            "mov_videoUrl": ['http://192.168.8.231:50008/download/video/infinitetalk_res_480p_greenbg_slide1v9_rmb1.mov'],
            "ppt_imageUrl": "http://192.168.8.231:50008/download/image/slide_001.png",
            "duration": "0:10",
            "narration": "欢迎同学们选修制造工程体验课程M09：个性化首饰设计及制作。在这门课程中，你将学习首饰设计的基本原理，掌握3D建模和加工制作技能，亲手打造属于自己的独特作品。"
        },
        {
            "id": 2,
            "title": "第二讲:中心简介-历史沿革",
            "slideContent": '<img src="slides/slide_002.png" style="max-width: 100%; height: auto;" alt="历史沿革">',
            "videoUrl": ['http://192.168.8.231:50008/download/video/infinitetalk_res_480p_greenbg_slide2v8_rmb.webm'],
            "mov_videoUrl": ['http://192.168.8.231:50008/download/video/infinitetalk_res_480p_greenbg_slide2v8_rmb.mov'],
            "ppt_imageUrl": "http://192.168.8.231:50008/download/image/slide_002.png",
            "duration": "0:10",
            "narration": "工训训练中心有着百年传承。从1921年的手工教学到金工实习，再到工训文化和工创理念，中心不断发展演进。如今，我们已经完成了从机械化、电气化到信息化、智能化的转型升级，始终走在工程教育创新的前沿。"
        },
        {
            "id": 3,
            "title": "第三讲:中心简介-功能定位",
            "slideContent": '<img src="slides/slide_003.png" style="max-width: 100%; height: auto;" alt="功能定位">',
            "videoUrl": ['http://192.168.8.231:50008/download/video/infinitetalk_res_480p_greenbg_slide3v8_rmb.webm'],
            "mov_videoUrl": ['http://192.168.8.231:50008/download/video/infinitetalk_res_480p_greenbg_slide3v8_rmb.mov'],
            "ppt_imageUrl": "http://192.168.8.231:50008/download/image/slide_003.png",
            "duration": "0:10",
            "narration": "清华大学基础工业训练中心，简称工训训练中心，是国际领先的工程实践与创新教育中心。中心传承工匠精神，弘扬创客文化，致力于培养学生的工程能力、劳动素质和创新创业能力，为同学们的梦想实现提供全方位支持。"
        },
        {
            "id": 4,
            "title": "第4讲:工艺介绍",
            "slideContent": '<img src="slides/slide_010.png" style="max-width: 100%; height: auto;" alt="工艺介绍">',
            "videoUrl": ['http://192.168.8.231:50008/download/video/infinitetalk_res_480p_teacher1_green_bg_slide10_shorter_rmb.webm', 'http://192.168.8.231:50008/download/video/infinitetalk_res_480p_student1_green_bg_slide10_rmb.webm',],
            "mov_videoUrl": [
                'http://192.168.8.231:50008/download/video/infinitetalk_res_480p_teacher1_green_bg_slide10_shorter_rmb.mov',
                'http://192.168.8.231:50008/download/video/infinitetalk_res_480p_student1_green_bg_slide10_rmb.mov',
            ],
            "ppt_imageUrl": "http://192.168.8.231:50008/download/image/slide_010.png",
            "duration": "0:25",
            "narration": "老师，我认为最具挑战性的步骤是熔模石膏型精密铸造。因为这一步不仅需要精确控制石膏的配比和焙烧温度，还要确保浇注时金属液的流动性和冷却速度，否则容易出现气孔或变形等问题。此外，后处理环节中的高温珐琅和钻石镶嵌也非常考验耐心和技巧，稍有不慎就可能影响首饰的整体美观和耐用性。不过，正是这些挑战让整个制作过程充满了成就感和艺术性！"
        }
    ]

    logger.info(f"Fetching course data for PPT: {ppt_name}")

    # 返回课程数据（后续可根据 ppt_name 从数据库查询）
    return {
        "pptName": ppt_name,
        "courses": course_data
    }
