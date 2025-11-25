import uuid
from datetime import datetime
from pathlib import Path

import aiofiles
import requests
from fastapi import APIRouter
from fastapi import Form, HTTPException

from api_server.api_loger import logger
from api_server.database import db_manager
from api_server.models import TaskInfo
from api_server.video_task_worker import video_task_worker

router = APIRouter(prefix="/video_task", tags=["video task"])


@router.post("/create", response_model=TaskInfo)
async def create_video_task(
        prompt: str = Form(default="一位年轻而充满活力的女教师正在讲解PPT演示文稿。她穿着天蓝色的衣服，长长的棕发自然垂落。"
                                   "她用富有表现力的手势强调重点内容。她的脸上洋溢着热情和温暖。自然光线充满整个空间，"
                                   "营造出充满灵感和创造力的学习环境。动态的中景镜头捕捉到她充满趣味的教学瞬间。",
            description="视频生成提示词"),
        image_path: str = Form(default="/workspace/InfiniteTalk/upload_image/img_20251125_023003_4810d60d.jpg",
            description="参考图片路径"),
        audio_text: str = Form(default="欢迎同学们选修制造工程体验课程M09：个性化首饰设计及制作。",
            description="需要转换的文本"),
        spk_name: str = Form(default="胡桃", description="cosyvoice的说话人id")
):
    """
    创建视频生成任务（立即返回任务ID，后台异步生成）
    步骤：
    1. 将 audio_text 转换为语音，获取音频路径
    2. 验证 image_path 文件是否存在
    3. 创建视频生成任务
    """
    logger.info('开始视频生产任务，参数是: ')
    try:
        # 第一步：请求文本转语音任务
        tts_api_url = "http://192.168.8.230:50002/tasks"
        tts_payload = {"spk_id": spk_name, "text": audio_text}
        tts_response = requests.post(tts_api_url, json=tts_payload)

        if tts_response.status_code != 200:
            raise HTTPException(status_code=500, detail="TTS任务创建失败")

        tts_task = tts_response.json()
        tts_task_id = tts_task.get("task_id")
        if not tts_task_id:
            raise HTTPException(status_code=500, detail="TTS任务ID获取失败")

        # 第二步：轮询TTS任务状态，直到任务完成
        tts_status_url = f"http://192.168.8.230:50002/tasks/{tts_task_id}"
        while True:
            tts_status_resp = requests.get(tts_status_url)
            if tts_status_resp.status_code != 200:
                raise HTTPException(status_code=500, detail="查询TTS任务状态失败")

            tts_status = tts_status_resp.json()
            if tts_status.get("status") == "done":
                break
            elif tts_status.get("status") in ["failed", "error"]:
                raise HTTPException(status_code=500, detail="TTS任务转换失败")

        # 第三步：下载音频文件到本地
        tts_audio_download_url = f"http://192.168.8.230:50002/tasks/{tts_task_id}/audio"
        audio_local_path = f"/workspace/InfiniteTalk/audio_file/audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.wav"
        async with aiofiles.open(audio_local_path, "wb") as audio_file:
            audio_data = requests.get(tts_audio_download_url).content
            await audio_file.write(audio_data)

        # 第四步：验证图片文件是否存在
        if not Path(image_path).exists():
            raise HTTPException(status_code=400, detail="Image file not found")

        # 第五步：创建任务ID
        task_id = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # 第六步：保存任务到数据库
        await db_manager.create_task(
            task_id=task_id,
            prompt=prompt,
            image_path=image_path,
            audio_path=audio_local_path
        )

        # 第七步：将任务加入队列
        await video_task_worker.add_task(task_id)
        logger.info(f"Task created: {task_id}")

        # 返回任务信息
        task_info = await db_manager.get_task_by_id(task_id)
        return task_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))
