from datetime import datetime, timedelta
from typing import List

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from api_server.config import config
from api_server.models import TaskInfo
from api_server.api_loger import logger
from typing import Optional, Dict, Any
from pathlib import Path

class DatabaseManager:
    """数据库管理器"""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.logger = logger

    async def connect(self):
        """连接到 MongoDB"""
        try:
            # 创建客户端连接
            self.client = AsyncIOMotorClient(
                config.MONGO_URL,
                maxPoolSize=config.MONGO_MAX_POOL_SIZE,
                minPoolSize=config.MONGO_MIN_POOL_SIZE,
                serverSelectionTimeoutMS=config.MONGO_SERVER_SELECTION_TIMEOUT
            )

            self.db = self.client[config.MONGO_DB_NAME]

            # 测试连接
            await self.db.command('ping')

            # 创建索引
            await self._create_indexes()

            self.logger.info(f"Successfully connected to MongoDB: {config.MONGO_DB_NAME}")

        except Exception as e:
            self.logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self):
        """断开 MongoDB 连接"""
        if self.client:
            self.client.close()
            self.logger.info("Disconnected from MongoDB")

    async def _create_indexes(self):
        """创建数据库索引"""
        try:
            # 图片索引
            await self.db[config.COLLECTION_IMAGES].create_index("person_name")
            await self.db[config.COLLECTION_IMAGES].create_index([("created_at", -1)])

            # 提示词索引
            await self.db[config.COLLECTION_PROMPTS].create_index("title")
            await self.db[config.COLLECTION_PROMPTS].create_index([("created_at", -1)])

            # 音频索引
            await self.db[config.COLLECTION_AUDIOS].create_index([("created_at", -1)])

            # 任务索引
            await self.db[config.COLLECTION_TASKS].create_index("status")
            await self.db[config.COLLECTION_TASKS].create_index([("created_at", -1)])
            await self.db[config.COLLECTION_TASKS].create_index([
                ("created_at", -1),
                ("status", 1)
            ])

            self.logger.info("Database indexes created successfully")

        except Exception as e:
            self.logger.warning(f"Error creating indexes: {e}")

    # ==================== 辅助方法 ====================

    @staticmethod
    def convert_objectid(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """将 MongoDB 的 ObjectId 转换为字符串"""
        if doc and "_id" in doc:
            doc["id"] = str(doc["_id"])
            del doc["_id"]
        return doc

    @staticmethod
    def convert_objectid_list(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量转换 ObjectId"""
        return [DatabaseManager.convert_objectid(doc) for doc in docs]

    # ==================== 图片相关操作 ====================

    async def create_image(self, person_name: str, image_name: str,
                           image_path: str) -> str:
        """创建图片记录"""
        image_doc = {
            "person_name": person_name,
            "image_name": image_name,
            "image_path": image_path,
            "created_at": datetime.now()
        }
        result = await self.db[config.COLLECTION_IMAGES].insert_one(image_doc)
        return str(result.inserted_id)

    async def get_image_by_id(self, image_id: str) -> Optional[Dict[str, Any]]:
        """根据 ID 查询图片"""
        try:
            image_doc = await self.db[config.COLLECTION_IMAGES].find_one(
                {"_id": ObjectId(image_id)}
            )
            return self.convert_objectid(image_doc)
        except Exception as e:
            self.logger.error(f"Error getting image {image_id}: {e}")
            return None

    async def search_images(self, person_name: Optional[str] = None,
                            limit: int = 100) -> List[Dict[str, Any]]:
        """搜索图片"""
        query = {}
        if person_name:
            query["person_name"] = {"$regex": person_name, "$options": "i"}

        cursor = self.db[config.COLLECTION_IMAGES].find(query) \
            .sort("created_at", -1).limit(limit)
        images = await cursor.to_list(length=limit)
        return self.convert_objectid_list(images)

    async def delete_image(self, image_id: str) -> bool:
        """删除图片记录"""
        try:
            result = await self.db[config.COLLECTION_IMAGES].delete_one(
                {"_id": ObjectId(image_id)}
            )
            return result.deleted_count > 0
        except Exception as e:
            self.logger.error(f"Error deleting image {image_id}: {e}")
            return False

    # ==================== 提示词相关操作 ====================

    async def create_prompt(self, title: str, content: str) -> str:
        """创建提示词记录"""
        prompt_doc = {
            "title": title,
            "content": content,
            "created_at": datetime.now()
        }
        result = await self.db[config.COLLECTION_PROMPTS].insert_one(prompt_doc)
        return str(result.inserted_id)

    async def get_prompt_by_id(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """根据 ID 查询提示词"""
        try:
            prompt_doc = await self.db[config.COLLECTION_PROMPTS].find_one(
                {"_id": ObjectId(prompt_id)}
            )
            return self.convert_objectid(prompt_doc)
        except Exception as e:
            self.logger.error(f"Error getting prompt {prompt_id}: {e}")
            return None

    async def search_prompts(self, title: Optional[str] = None,
                             limit: int = 100) -> List[Dict[str, Any]]:
        """搜索提示词"""
        query = {}
        if title:
            query["title"] = {"$regex": title, "$options": "i"}

        cursor = self.db[config.COLLECTION_PROMPTS].find(query) \
            .sort("created_at", -1).limit(limit)
        prompts = await cursor.to_list(length=limit)
        return self.convert_objectid_list(prompts)

    async def delete_prompt(self, prompt_id: str) -> bool:
        """删除提示词"""
        try:
            result = await self.db[config.COLLECTION_PROMPTS].delete_one(
                {"_id": ObjectId(prompt_id)}
            )
            return result.deleted_count > 0
        except Exception as e:
            self.logger.error(f"Error deleting prompt {prompt_id}: {e}")
            return False

    # ==================== 音频相关操作 ====================

    async def create_audio(self, audio_id: str, audio_path: str,
                           audio_text: str, original_filename: str) -> str:
        """创建音频记录"""
        audio_doc = {
            "_id": audio_id,
            "audio_path": audio_path,
            "audio_text": audio_text,
            "original_filename": original_filename,
            "created_at": datetime.now()
        }
        await self.db[config.COLLECTION_AUDIOS].insert_one(audio_doc)
        return audio_id

    async def get_audio_by_id(self, audio_id: str) -> Optional[Dict[str, Any]]:
        """根据 ID 查询音频"""
        try:
            audio_doc = await self.db[config.COLLECTION_AUDIOS].find_one(
                {"_id": audio_id}
            )
            if audio_doc:
                audio_doc["id"] = audio_doc["_id"]
                del audio_doc["_id"]
            return audio_doc
        except Exception as e:
            self.logger.error(f"Error getting audio {audio_id}: {e}")
            return None

    async def get_recent_audios(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最新的音频列表"""
        cursor = self.db[config.COLLECTION_AUDIOS].find() \
            .sort("created_at", -1).limit(limit)
        audios = await cursor.to_list(length=limit)

        for audio in audios:
            audio["id"] = audio["_id"]
            del audio["_id"]

        return audios

    async def delete_audio(self, audio_id: str) -> bool:
        """删除音频记录"""
        try:
            result = await self.db[config.COLLECTION_AUDIOS].delete_one(
                {"_id": audio_id}
            )
            return result.deleted_count > 0
        except Exception as e:
            self.logger.error(f"Error deleting audio {audio_id}: {e}")
            return False

    # ==================== 任务相关操作 ====================
    async def create_task(self, task_id: str, prompt: str, image_path: str, audio_path: str) -> str:

        """创建任务记录"""
        task_doc = {
            "_id": task_id,
            "status": "pending",
            "prompt": prompt,
            "image_path": image_path,
            "audio_path": audio_path,
            "created_at": datetime.now(),
        }
        await self.db[config.COLLECTION_TASKS].insert_one(task_doc)
        logger.info(f"创建任务记录 task_doc: {task_doc}")
        return task_id

    async def get_task_by_id(self, task_id: str) -> Optional[TaskInfo]:
        """根据 ID 查询任务，返回 TaskInfo 对象"""
        try:
            task_doc = await self.db[config.COLLECTION_TASKS].find_one(
                {"_id": task_id}
            )
            logger.info(f"get_task_by_id task_doc: {task_doc}")
            if task_doc:
                # 转换 _id 为 id
                task_doc["id"] = task_doc["_id"]
                del task_doc["_id"]
                # 转换为 Pydantic 模型
                return TaskInfo(**task_doc)
            return None
        except Exception as e:
            self.logger.error(f"Error getting task {task_id}: {e}")
            return None

    @staticmethod
    def sanitize_for_mongo(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理数据以适配 MongoDB（转换 Path 对象为字符串）
        Args:
            data: 原始数据字典
        Returns:
            清理后的数据字典
        """
        cleaned = {}
        for key, value in data.items():
            if isinstance(value, Path):
                cleaned[key] = str(value)
            elif isinstance(value, list):
                cleaned[key] = [str(v) if isinstance(v, Path) else v for v in value]
            else:
                cleaned[key] = value
        return cleaned

    async def update_task_status(
            self,
            task_id: str,
            status: str,
            pid: Optional[int] = None,
            started_at: Optional[datetime] = None,
            ended_at: Optional[datetime] = None,
            error_message: Optional[str] = None,
            video_path: Optional[str] = None,
            video_download_url: Optional[str] = None,
            log_path: Optional[str] = None,
            command: Optional[List[str]] = None,
            generate_video_file: Optional[str] = None,
            uptime: Optional[float] = None
    ):
        """更新任务状态"""
        try:
            logger.info(f"🟢 [进入函数] update_task_status")
            logger.info(f"🟢 [参数] task_id={task_id}, status={status}, pid={pid}")
            # 构建更新数据
            update_data = {
                "status": status,
                "command": command,
            }
            if command is not None:
                update_data["command"] = command
            if log_path is not None:
                update_data["log_path"] = log_path
            if pid is not None:
                update_data["pid"] = pid
            if started_at is not None:
                update_data["started_at"] = started_at
                update_data["created_at"] = started_at
            if ended_at is not None:
                update_data["ended_at"] = ended_at
                update_data["completed_at"] = ended_at
            if error_message is not None:
                update_data["error_message"] = error_message
            if video_path is not None:
                update_data["video_path"] = video_path
            if video_download_url is not None:
                update_data["video_download_url"] = video_download_url
            if uptime is not None:
                update_data["uptime"] = uptime
            if generate_video_file is not None:
                update_data["generate_video_file"] = generate_video_file
            # 清理数据（转换 Path 对象）
            update_data = self.sanitize_for_mongo(update_data)
            logger.info(f'🟢 [准备更新] 字段数量={update_data}')
            result = await self.db[config.COLLECTION_TASKS].update_one(
                {"_id": task_id},
                {"$set": update_data}
            )
            logger.info(f'🟢 [更新结果] matched={result.matched_count}, modified={result.modified_count}')
            if result.matched_count == 0:
                logger.warning(f'⚠️ 未找到任务: {task_id}')
            else:
                logger.info(f'✅ 任务状态更新成功: {task_id} -> {status}')
            return result
        except Exception as e:
            logger.error(f"🔴 [异常] 更新失败: {e}", exc_info=True)
            raise e

    async def update_task_completed(self, task_id: str, video_path: str,
                                    video_download_url: str):
        """更新任务为完成状态"""
        await self.update_task_status(
            task_id,
            "completed",
            video_path=video_path,
            video_download_url=video_download_url,
            ended_at=datetime.now()
        )

    async def update_task_failed(self, task_id: str, error_message: str):
        """更新任务为失败状态"""
        await self.update_task_status(
            task_id,
            "failed",
            task_failed=error_message,
            ended_at=datetime.now()
        )

    async def get_tasks(self, status: Optional[str] = None,
                        limit: int = 20) -> List[Dict[str, Any]]:
        """获取任务列表"""
        query = {}
        if status:
            query["status"] = status

        cursor = self.db[config.COLLECTION_TASKS].find(query) \
            .sort("created_at", -1).limit(limit)
        tasks = await cursor.to_list(length=limit)

        for task in tasks:
            task["id"] = task["_id"]
            del task["_id"]

        return tasks

    async def delete_task(self, task_id: str) -> bool:
        """删除任务记录"""
        try:
            result = await self.db[config.COLLECTION_TASKS].delete_one(
                {"_id": task_id}
            )
            return result.deleted_count > 0
        except Exception as e:
            self.logger.error(f"Error deleting task {task_id}: {e}")
            return False

    async def cleanup_old_tasks(self, days: int = None) -> int:
        """清理旧任务"""
        if days is None:
            days = config.TASK_RETENTION_DAYS

        cutoff_date = datetime.now() - timedelta(days=days)

        result = await self.db[config.COLLECTION_TASKS].delete_many({
            "created_at": {"$lt": cutoff_date},
            "status": {"$in": ["completed", "failed"]}
        })

        self.logger.info(f"Cleaned up {result.deleted_count} old tasks")
        return result.deleted_count

    async def update_task_progress(
            self,
            task_id: str,
            stage: str,
            progress: int,
            message: str = ""
    ):
        """更新任务进度"""
        try:
            progress_data = {
                "progress.stage": stage,
                "progress.progress": progress,
                "progress.message": message,
                "progress.updated_at": datetime.now()
            }

            result = await self.db[config.COLLECTION_TASKS].update_one(
                {"_id": task_id},
                {"$set": progress_data}
            )

            logger.info(f"✅ 更新进度: {task_id} - {stage} ({progress}%)")
            return result

        except Exception as e:
            logger.error(f"🔴 更新进度失败: {e}", exc_info=True)
            raise

    async def append_task_log(
            self,
            task_id: str,
            message: str,
            level: str = "INFO"
    ):
        """追加任务日志"""
        try:
            log_entry = {
                "timestamp": datetime.now(),
                "level": level,
                "message": message
            }

            result = await self.db[config.COLLECTION_TASKS].update_one(
                {"_id": task_id},
                {"$push": {"logs": log_entry}}
            )

            logger.debug(f"📝 追加日志: {task_id} - {message}")
            return result

        except Exception as e:
            logger.error(f"🔴 追加日志失败: {e}", exc_info=True)
            raise

    async def get_task_logs(
            self,
            task_id: str,
            limit: int = 100
    ) -> List[Dict]:
        """获取任务日志（最新的N条）"""
        try:
            task_doc = await self.db[config.COLLECTION_TASKS].find_one(
                {"_id": task_id},
                {"logs": {"$slice": -limit}}  # 获取最后N条
            )

            if task_doc and "logs" in task_doc:
                return task_doc["logs"]
            return []

        except Exception as e:
            logger.error(f"🔴 获取日志失败: {e}")
            return []


# 创建全局数据库管理器实例
db_manager = DatabaseManager()


# 便捷函数
async def get_db() -> DatabaseManager:
    """获取数据库管理器实例"""
    return db_manager
