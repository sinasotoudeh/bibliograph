from typing import Dict, Any, List
from datetime import datetime
import structlog
from motor.motor_asyncio import AsyncIOMotorCollection
from src.core.database.mongodb import MongoDBClient

logger = structlog.get_logger(__name__)


class ScrapingLogRepository:
    """Handles scraping task logs stored in MongoDB."""

    COLLECTION_NAME = "scraping_logs"  # ✅ تعریف مستقیم بدون نیاز به ScrapingLog.Config

    def __init__(self, mongodb_client: MongoDBClient):
        db = mongodb_client.get_database()
        self.collection: AsyncIOMotorCollection = db[self.COLLECTION_NAME]

    async def insert_log(self, data: Dict[str, Any]) -> None:
        try:
            now = datetime.utcnow()
            data.setdefault("created_at", now)
            data["updated_at"] = now
            await self.collection.insert_one(data)

            logger.info(
                "scrape_log.inserted",
                task_id=data.get("task_id"),
                author=data.get("current_author"),
                source=data.get("source"),
            )
        except Exception as e:
            logger.error("scrape_log.insert_failed", error=str(e), data=data)
            raise

    async def update_progress(self, task_id: str, meta: Dict[str, Any]) -> None:
        try:
            meta["updated_at"] = datetime.utcnow()
            await self.collection.update_one(
                {"task_id": task_id},
                {"$set": meta},
                upsert=True
            )
            logger.info(
                "scrape_log.updated",
                task_id=task_id,
                progress=meta.get("progress"),
                current_author=meta.get("current_author"),
            )
        except Exception as e:
            logger.error("scrape_log.update_failed", task_id=task_id, error=str(e))
            raise

    async def get_recent_logs(self, source: str, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            cursor = self.collection.find(
                {"source": source}
            ).sort("updated_at", -1).limit(limit)
            logs = await cursor.to_list(length=limit)
            logger.debug("scrape_log.retrieved", source=source, count=len(logs))
            return logs
        except Exception as e:
            logger.error("scrape_log.fetch_failed", source=source, error=str(e))
            raise
