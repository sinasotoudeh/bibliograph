"""
Dependency Injection for FastAPI
Provides reusable dependencies for routes
"""

from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import DatabaseManager
from src.repositories.book_repo import BookRepository


def get_db_manager(request: Request) -> DatabaseManager:
    """
    Get DatabaseManager from app state
    
    Args:
        request: FastAPI request object
        
    Returns:
        DatabaseManager instance from app.state
    """
    return request.app.state.db_manager


async def get_postgres_session(
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Get PostgreSQL async session
    
    Usage:
        @app.get("/books")
        async def get_books(session: AsyncSession = Depends(get_postgres_session)):
            ...
    """
    async with db_manager.postgres.get_session() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}",
            )
        finally:
            await session.close()


async def get_book_repository(
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> BookRepository:
    """
    Get BookRepository instance
    
    Usage:
        @app.get("/books")
        async def get_books(repo: BookRepository = Depends(get_book_repository)):
            ...
    """
    # ✅ استفاده از mongodb.db یا mongodb.client بسته به پیاده‌سازی MongoDBClient
    return BookRepository(db_manager.mongodb)


async def get_mongodb_client(
    db_manager: DatabaseManager = Depends(get_db_manager),
):
    """Get MongoDB client"""
    return db_manager.mongodb


async def get_redis_cache(
    db_manager: DatabaseManager = Depends(get_db_manager),
):
    """Get Redis cache client"""
    return db_manager.cache


async def get_elasticsearch_client(
    db_manager: DatabaseManager = Depends(get_db_manager),
):
    """Get Elasticsearch client"""
    return db_manager.elasticsearch
