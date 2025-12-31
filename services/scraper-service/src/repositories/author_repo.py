from datetime import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId
import structlog
from src.core.database.mongodb import MongoDBClient

logger = structlog.get_logger(__name__)

class AuthorRepository:
    def __init__(self, mongodb_client: MongoDBClient):
        self.db = mongodb_client.get_database()
        self.collection = self.db["authors"]

    async def create(self, author_data: Dict[str, Any]) -> str:
        now = datetime.utcnow()
        author_data["created_at"] = now
        author_data["updated_at"] = now
        result = await self.collection.insert_one(author_data)
        logger.info("author_created", id=str(result.inserted_id))
        return str(result.inserted_id)

    async def get_by_index_range(self, start: int, end: int) -> List[Dict[str, Any]]:
        cursor = self.collection.find({
            "author_index_number": {"$gte": start, "$lte": end}
        }).sort("author_index_number", 1)
        authors = await cursor.to_list(None)
        logger.info("authors_range_fetched", count=len(authors))
        return authors
