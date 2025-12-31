"""
Book Repository - MongoDB operations for books
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import structlog
from pymongo.errors import DuplicateKeyError
from pymongo import ReturnDocument
from bson import ObjectId

from src.core.database.mongodb import MongoDBClient

logger = structlog.get_logger(__name__)


class BookNotFoundError(Exception):
    """Raised when book is not found"""
    pass


class DuplicateBookError(Exception):
    """Raised when trying to create duplicate book"""
    pass


class BookRepository:
    """
    Repository for Book operations in MongoDB
    """

    def __init__(self, mongodb_client: MongoDBClient):
        """
        Initialize repository with MongoDB client
        
        Args:
            mongodb_client: MongoDBClient instance
        """
        self.mongodb_client = mongodb_client
        # ✅ استفاده از get_database() برای رعایت سازگاری async
        self.db = mongodb_client.get_database()
        self.collection = self.db["books"]

    async def create_indexes(self) -> None:
        """
        Create necessary indexes for books collection
        """
        try:
            await self.collection.create_index(
                "isbn",
                unique=True,
                name="isbn_unique_idx"
            )
            await self.collection.create_index("title", name="title_idx")
            await self.collection.create_index(
                [("authors", 1), ("title", 1)],
                name="author_title_idx"
            )
            await self.collection.create_index("created_at", name="created_at_idx")

            logger.info("book_indexes_created")

        except Exception as e:
            logger.error("book_indexes_creation_failed", error=str(e))
            raise

    async def create(self, book_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new book
        
        Args:
            book_data: Book data dictionary
            
        Returns:
            Created book with _id
            
        Raises:
            DuplicateBookError: If book with same ISBN exists
        """
        try:
            # Add timestamps
            now = datetime.utcnow()
            book_data["created_at"] = now
            book_data["updated_at"] = now

            result = await self.collection.insert_one(book_data)

            created_book = await self.collection.find_one({"_id": result.inserted_id})

            logger.info(
                "book_created",
                book_id=str(result.inserted_id),
                isbn=book_data.get("isbn"),
                title=book_data.get("title"),
            )
            return created_book

        except DuplicateKeyError:
            logger.warning("duplicate_book", isbn=book_data.get("isbn"))
            raise DuplicateBookError(f"Book with ISBN {book_data.get('isbn')} already exists")
        except Exception as e:
            logger.error("book_creation_failed", error=str(e), data=book_data)
            raise

    async def get_by_id(self, book_id: str) -> Optional[Dict[str, Any]]:
        """
        Get book by ID
        
        Args:
            book_id: Book ObjectId as string
            
        Returns:
            Book document or None
        """
        try:
            book = await self.collection.find_one({"_id": ObjectId(book_id)})
            return book
        except Exception as e:
            logger.error("get_book_by_id_failed", book_id=book_id, error=str(e))
            raise

    async def get_by_isbn(self, isbn: str) -> Optional[Dict[str, Any]]:
        """
        Get book by ISBN
        
        Args:
            isbn: Book ISBN
            
        Returns:
            Book document or None
        """
        try:
            book = await self.collection.find_one({"isbn": isbn})
            return book
        except Exception as e:
            logger.error("get_book_by_isbn_failed", isbn=isbn, error=str(e))
            raise

    async def update(self, book_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update book
        
        Args:
            book_id: Book ObjectId as string
            update_data: Fields to update
            
        Returns:
            Updated book document
            
        Raises:
            BookNotFoundError: If book not found
        """
        try:
            update_data["updated_at"] = datetime.utcnow()

            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(book_id)},
                {"$set": update_data},
                return_document=ReturnDocument.AFTER
            )

            if not result:
                raise BookNotFoundError(f"Book with ID {book_id} not found")

            logger.info("book_updated", book_id=book_id, fields=list(update_data.keys()))
            return result

        except Exception as e:
            logger.error("book_update_failed", book_id=book_id, error=str(e))
            raise

    async def delete(self, book_id: str) -> bool:
        """
        Delete book
        
        Args:
            book_id: Book ObjectId as string
            
        Returns:
            True if deleted, False if not found
        """
        try:
            result = await self.collection.delete_one({"_id": ObjectId(book_id)})
            if result.deleted_count == 0:
                return False

            logger.info("book_deleted", book_id=book_id)
            return True

        except Exception as e:
            logger.error("book_deletion_failed", book_id=book_id, error=str(e))
            raise

    async def list_books(
        self,
        skip: int = 0,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        List books with pagination and filters
        
        Args:
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            filters: MongoDB query filters
            
        Returns:
            List of book documents
        """
        try:
            query = filters or {}
            cursor = self.collection.find(query).skip(skip).limit(limit)
            books = await cursor.to_list(length=limit or 10)
            return books

        except Exception as e:
            logger.error("list_books_failed", error=str(e))
            raise

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count books matching filters
        
        Args:
            filters: MongoDB query filters
            
        Returns:
            Number of matching documents
        """
        try:
            query = filters or {}
            count = await self.collection.count_documents(query)
            return count
        except Exception as e:
            logger.error("count_books_failed", error=str(e))
            raise
