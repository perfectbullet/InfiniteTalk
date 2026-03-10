import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiohttp
from fastapi import UploadFile, HTTPException

from api_server.api_loger import logger
from api_server.config import config


# ==================== 辅助函数 ====================
def generate_unique_filename(prefix: str, extension: str) -> str:
    """生成唯一文件名"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"{prefix}_{timestamp}_{unique_id}{extension}"


def validate_file_size(file: UploadFile, max_size: int):
    """验证文件大小"""
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)"
        )


async def call_green_background_service(image_path: str) -> Optional[str]:
    """
    调用绿幕背景替换服务处理图片
    
    Args:
        image_path: 原始图片的完整路径
        
    Returns:
        处理后的图片路径，失败时返回 None
    """
    try:
        # 检查原图是否存在
        if not Path(image_path).exists():
            logger.error(f"原始图片不存在: {image_path}")
            return None
            
        # 构建完整的 API URL（包含查询参数）
        bgc = config.GREEN_BACKGROUND_BGC
        url = f"{config.GREEN_BACKGROUND_SERVICE_URL}?bgc={bgc}"
        
        # 准备表单数据
        form = aiohttp.FormData()
        
        # 添加文件
        with open(image_path, "rb") as f:
            file_content = f.read()
            filename = Path(image_path).name
            form.add_field("file", file_content, filename=filename, content_type="image/png")
        
        # 添加其他参数（使用配置的模型）
        form.add_field("model", config.GREEN_BACKGROUND_MODEL)
        form.add_field("a", "false")
        form.add_field("af", "240")
        form.add_field("ab", "10")
        form.add_field("ae", "10")
        form.add_field("om", "false")
        form.add_field("ppm", "false")
        
        # 发送请求
        timeout = aiohttp.ClientTimeout(total=config.GREEN_BACKGROUND_SERVICE_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            logger.info(f"调用绿幕服务: {url}, 模型: {config.GREEN_BACKGROUND_MODEL}")
            
            async with session.post(url, data=form) as response:
                if response.status != 200:
                    logger.error(f"绿幕服务返回错误: status={response.status}")
                    return None
                
                # 读取返回的图片
                processed_image_data = await response.read()
                
                # 生成新的文件名（在原文件名基础上添加后缀）
                original_path = Path(image_path)
                new_filename = f"{original_path.stem}_green_bg_removed{original_path.suffix}"
                new_file_path = original_path.parent / new_filename
                
                # 保存处理后的图片
                with open(new_file_path, "wb") as f:
                    f.write(processed_image_data)
                
                logger.info(f"绿幕处理成功: {new_file_path}")
                return str(new_file_path)
                
    except aiohttp.ClientConnectorError as e:
        logger.error(f"无法连接到绿幕服务 {config.GREEN_BACKGROUND_SERVICE_URL}: {e}")
        return None
    except aiohttp.ClientError as e:
        logger.error(f"绿幕服务请求失败: {e}")
        return None
    except Exception as e:
        logger.exception(f"调用绿幕服务时发生未知错误: {e}")
        return None


async def convert_video_no_background(
    video_path: str,
    output_format: str = ".webm",
    similarity: float = 0.35,
    blend: float = 0.1,
    despill_mix: float = 0.9,
    despill_expand: float = 0.1
) -> Optional[str]:
    """
    调用绿幕转换服务处理视频，去除绿色背景
    
    Args:
        video_path: 原始视频的完整路径
        output_format: 输出格式（默认 .webm）
        similarity: 绿色相似度阈值 (0-1)
        blend: 边缘混合程度 (0-1)
        despill_mix: 去绿边混合系数 (0-1)
        despill_expand: 去绿边扩展范围 (0-1)
        
    Returns:
        处理后的视频路径，失败时返回 None
    """
    import asyncio
    
    try:
        # 检查原视频是否存在
        video_file = Path(video_path)
        if not video_file.exists():
            logger.error(f"原始视频不存在: {video_path}")
            return None
        
        # 构建输出文件路径（no_bg_原文件名.output_format）
        output_filename = f"no_bg_{video_file.stem}{output_format}"
        output_path = video_file.parent / output_filename
        
        # 如果输出文件已存在，直接返回
        if output_path.exists():
            logger.info(f"转换后的视频已存在: {output_path}")
            return str(output_path)
        
        # 构建请求数据
        request_data = {
            "input": str(video_path),
            "output_format": output_format,
            "similarity": similarity,
            "blend": blend,
            "despill_mix": despill_mix,
            "despill_expand": despill_expand
        }
        
        # 发送请求到绿幕转换服务
        url = f"http://{config.API_HOST}:{config.API_PORT}/api/green_background/convert"
        timeout = aiohttp.ClientTimeout(total=600)  # 10分钟超时
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            logger.info(f"调用绿幕转换服务: {url}")
            logger.info(f"请求参数: {request_data}")
            
            async with session.post(url, json=request_data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"绿幕转换服务返回错误: status={response.status}, error={error_text}")
                    return None
                
                result = await response.json()
                logger.info(f"绿幕转换服务响应: {result}")
                
                # 检查任务状态
                if result.get("status") == "completed":
                    # 文件已存在，直接返回
                    return result.get("output_path")
                elif result.get("status") == "started":
                    # 任务已启动，等待完成
                    task_id = result.get("task_id")
                    output_path_str = result.get("output_path")
                    
                    logger.info(f"绿幕转换任务已启动: task_id={task_id}")
                    
                    # 轮询检查任务状态（最多等待 10 分钟）
                    max_wait_time = 600  # 10分钟
                    check_interval = 10  # 每10秒检查一次
                    elapsed_time = 0
                    
                    while elapsed_time < max_wait_time:
                        await asyncio.sleep(check_interval)
                        elapsed_time += check_interval
                        
                        # 直接检查文件是否存在
                        if Path(output_path_str).exists():
                            logger.info(f"绿幕转换完成: {output_path_str}")
                            return output_path_str
                        
                        logger.debug(f"等待绿幕转换完成... ({elapsed_time}/{max_wait_time}s)")
                    
                    logger.error(f"绿幕转换超时: task_id={task_id}")
                    return None
                else:
                    logger.error(f"未知的任务状态: {result.get('status')}")
                    return None
                
    except aiohttp.ClientConnectorError as e:
        logger.error(f"无法连接到绿幕转换服务: {e}")
        return None
    except aiohttp.ClientError as e:
        logger.error(f"绿幕转换服务请求失败: {e}")
        return None
    except Exception as e:
        logger.exception(f"调用绿幕转换服务时发生未知错误: {e}")
        return None