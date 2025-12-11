import asyncio
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse

from api_server.api_loger import logger
from api_server.config import config
from api_server.database import db_manager

router = APIRouter(prefix="/tasks_logs", tags=["Task Logs"])

# ===== 配置常量 =====
LOG_BASE_DIR = config.LOG_DIR
DEFAULT_TAIL_LINES = 100
MAX_TAIL_LINES = 10000
LOG_STREAM_INTERVAL = 0.5  # 秒
MAX_LOG_SIZE = 100 * 1024 * 1024  # 100MB


# ===== 辅助函数 =====
def get_log_path(task_id: str) -> Path:
    """
    获取任务日志文件路径

    Args:
        task_id: 任务ID

    Returns:
        Path: 日志文件路径

    Raises:
        HTTPException: 如果任务ID无效
    """
    # 验证任务ID格式（防止路径遍历攻击）
    if not task_id or ".." in task_id or "/" in task_id or "\\" in task_id:
        raise HTTPException(
            status_code=400,
            detail="无效的任务ID格式"
        )

    log_path = LOG_BASE_DIR / f"task_{task_id}.log"

    if not log_path.exists():
        logger.warning(f"日志文件不存在: {log_path}")
        raise HTTPException(
            status_code=404,
            detail=f"任务 {task_id} 的日志文件不存在"
        )

    # 检查文件大小
    file_size = log_path.stat().st_size
    if file_size > MAX_LOG_SIZE:
        logger.warning(f"日志文件过大: {file_size} bytes")

    return log_path


async def check_task_status(task_id: str) -> Optional[str]:
    """
    检查任务状态

    Args:
        task_id: 任务ID

    Returns:
        Optional[str]: 任务状态，如果任务不存在则返回 None
    """
    try:
        task_doc = await db_manager.get_task_by_id(task_id)
        return task_doc.status if task_doc else None
    except Exception as e:
        logger.error(f"获取任务状态失败 [{task_id}]: {str(e)}")
        return None


def is_task_finished(status: Optional[str]) -> bool:
    """判断任务是否已完成"""
    return status in ['completed', 'failed', 'cancelled']


# ===== 路由端点 =====

@router.get(
    "/{task_id}/logs",
    summary="获取任务日志",
    description="获取指定任务的日志内容，支持实时跟踪模式",
    response_description="返回日志内容或日志流"
)
async def get_task_logs(
        task_id: str,
        follow: bool = Query(
            False,
            description="是否实时跟踪日志（类似 `tail -f`）"
        )
):
    """
    ## 📋 获取任务日志

    ### 功能说明
    - **普通模式** (`follow=false`): 一次性返回全部日志内容
    - **跟踪模式** (`follow=true`): 实时流式返回日志，持续监控新内容

    ### 参数
    - `task_id`: 任务ID
    - `follow`: 是否启用跟踪模式

    ### 返回值
    - **普通模式**: JSON 格式，包含完整日志
    - **跟踪模式**: 文本流 (text/event-stream)

    ### 示例
    ```bash
    # 获取全部日志
    GET /api/tasks/{task_id}/logs

    # 实时跟踪日志
    GET /api/tasks/{task_id}/logs?follow=true
    ```
    """
    log_path = get_log_path(task_id)
    logger.info(f"{'实时' if follow else '静态'}读取日志: {log_path}")

    if follow:
        # ===== 实时跟踪模式 =====
        async def log_streamer():
            """异步日志流生成器"""
            try:
                # 打开文件
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # 1. 先读取已有内容
                    logger.info("开始读取已有日志内容")
                    line_count = 0

                    for line in f:
                        yield f"data: {line}\n\n"  # SSE 格式
                        line_count += 1

                    logger.info(f"✅ 已读取 {line_count} 行历史日志")

                    # 2. 持续监控新内容
                    logger.info("👀 开始监控新日志...")
                    no_data_count = 0
                    max_no_data_iterations = 120  # 60秒无数据则停止 (120 * 0.5s)

                    while True:
                        line = f.readline()

                        if line:
                            yield f"data: {line}\n\n"
                            no_data_count = 0  # 重置计数器
                        else:
                            # 检查任务状态
                            status = await check_task_status(task_id)

                            if is_task_finished(status):
                                logger.info(f"✅ 任务已完成 (status={status})，停止监控")
                                yield f"data: [任务已完成: {status}]\n\n"
                                break

                            # 计数无数据次数
                            no_data_count += 1
                            if no_data_count >= max_no_data_iterations:
                                logger.warning("⏱️ 长时间无新日志，自动停止监控")
                                yield "data: [长时间无新日志，自动停止监控]\n\n"
                                break

                            # 等待新数据
                            await asyncio.sleep(LOG_STREAM_INTERVAL)

                logger.info("🏁 日志流传输结束")

            except asyncio.CancelledError:
                logger.info("❌ 客户端断开连接，停止日志流")
                raise
            except Exception as e:
                logger.error(f"❌ 日志流传输错误: {str(e)}", exc_info=True)
                yield f"data: [错误: {str(e)}]\n\n"

        return StreamingResponse(
            log_streamer(),
            media_type="text/event-stream",  # 使用 SSE 格式
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
                "Connection": "keep-alive"
            }
        )
    else:
        # ===== 普通模式：一次性返回全部日志 =====
        try:
            file_size = log_path.stat().st_size

            # 检查文件大小，过大时给出警告
            if file_size > 10 * 1024 * 1024:  # 10MB
                logger.warning(f"⚠️ 日志文件较大: {file_size / 1024 / 1024:.2f} MB")

            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            logger.info(f"✅ 成功读取日志，大小: {len(content)} 字符")

            return JSONResponse(
                content={
                    "task_id": task_id,
                    "logs": content,
                    "size": file_size,
                    "lines": content.count('\n')
                }
            )

        except Exception as e:
            logger.error(f"❌ 读取日志失败: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"读取日志失败: {str(e)}"
            )


# @router.get(
#     "/{task_id}/logs/tail",
#     summary="获取最后N行日志",
#     description="使用 `tail` 命令获取日志的最后若干行",
#     response_description="返回最后N行日志内容"
# )
async def get_task_logs_tail(
        task_id: str,
        lines: int = Query(
            DEFAULT_TAIL_LINES,
            ge=1,
            le=MAX_TAIL_LINES,
            description=f"要获取的行数 (1-{MAX_TAIL_LINES})"
        )
):
    """
    ## 📜 获取最后N行日志

    ### 功能说明
    高效获取日志文件的最后若干行，适用于快速查看最新日志。

    ### 参数
    - `task_id`: 任务ID
    - `lines`: 要获取的行数（默认 100 行）

    ### 返回值
    JSON 格式，包含最后N行日志

    ### 示例
    ```bash
    # 获取最后100行
    GET /api/tasks/{task_id}/logs/tail

    # 获取最后500行
    GET /api/tasks/{task_id}/logs/tail?lines=500
    ```
    """
    log_path = get_log_path(task_id)
    logger.info(f"📜 获取最后 {lines} 行日志: {log_path}")

    try:
        # 使用 tail 命令（更高效）
        result = subprocess.run(
            ['tail', '-n', str(lines), str(log_path)],
            capture_output=True,
            text=True,
            timeout=10,  # 10秒超时
            encoding='utf-8',
            errors='ignore'
        )

        if result.returncode != 0:
            logger.error(f"❌ tail 命令执行失败: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"获取日志失败: {result.stderr}"
            )

        log_content = result.stdout
        actual_lines = log_content.count('\n')

        logger.info(f"✅ 成功获取 {actual_lines} 行日志")

        return JSONResponse(
            content={
                "task_id": task_id,
                "logs": log_content,
                "requested_lines": lines,
                "actual_lines": actual_lines
            }
        )

    except subprocess.TimeoutExpired:
        logger.error("❌ tail 命令执行超时")
        raise HTTPException(
            status_code=500,
            detail="获取日志超时，请稍后重试"
        )
    except Exception as e:
        logger.error(f"❌ 获取日志失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取日志失败: {str(e)}"
        )


# @router.get(
#     "/{task_id}/logs/download",
#     summary="下载日志文件",
#     description="下载完整的日志文件",
#     response_class=StreamingResponse
# )
async def download_task_logs(task_id: str):
    """
    ## 💾 下载日志文件

    ### 功能说明
    下载完整的日志文件到本地

    ### 参数
    - `task_id`: 任务ID

    ### 返回值
    文件流（application/octet-stream）

    ### 示例
    ```bash
    GET /api/tasks/{task_id}/logs/download
    ```
    """
    log_path = get_log_path(task_id)
    logger.info(f"💾 下载日志文件: {log_path}")

    try:
        def file_iterator():
            """文件迭代器"""
            with open(log_path, 'rb') as f:
                while chunk := f.read(8192):  # 8KB 每次
                    yield chunk

        file_size = log_path.stat().st_size

        return StreamingResponse(
            file_iterator(),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="task_{task_id}.log"',
                "Content-Length": str(file_size)
            }
        )
    except Exception as e:
        logger.error(f"❌ 下载日志失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"下载日志失败: {str(e)}"
        )


# @router.delete(
#     "/{task_id}/logs",
#     summary="🗑删除日志文件",
#     description="删除指定任务的日志文件"
# )
async def delete_task_logs(task_id: str):
    """
    ## 🗑️ 删除日志文件

    ### 功能说明
    删除指定任务的日志文件（谨慎操作）

    ### 参数
    - `task_id`: 任务ID

    ### 返回值
    删除结果

    ### 示例
    ```bash
    DELETE /api/tasks/{task_id}/logs
    ```
    """
    log_path = get_log_path(task_id)

    try:
        log_path.unlink()
        logger.info(f"🗑️ 成功删除日志文件: {log_path}")

        return JSONResponse(
            content={
                "message": "日志文件已删除",
                "task_id": task_id,
                "path": str(log_path)
            }
        )
    except Exception as e:
        logger.error(f"❌ 删除日志失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"删除日志失败: {str(e)}"
        )