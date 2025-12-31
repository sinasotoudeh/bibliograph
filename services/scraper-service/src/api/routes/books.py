"""
Books CRUD Endpoints
Handles MongoDB book operations for Scraper-Service.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.repositories.book_repo import (
    BookRepository,
    BookNotFoundError,
    DuplicateBookError,
)
from src.schemas.book import BookCreate, BookUpdate, BookResponse
from ..dependencies import get_book_repository

router = APIRouter(prefix="/books", tags=["Books"])
logger = structlog.get_logger(__name__)

# ============================================================
# ============= CRUD Endpoints for MongoDB Books =============
# ============================================================

@router.get("", response_model=Dict[str, Any])
async def list_books(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in title/authors"),
    source: Optional[str] = Query(None, description="Filter by source URL pattern"),
    language: Optional[str] = Query(None, description="Filter by language"),
    repo: BookRepository = Depends(get_book_repository),
) -> Dict[str, Any]:
    """List books with pagination and optional filters."""
    logger.info(
        "books_list_requested",
        page=page,
        page_size=page_size,
        search=search,
        source=source,
        language=language,
    )

    try:
        skip = (page - 1) * page_size
        filters: Dict[str, Any] = {}

        if source:
            filters["source_url"] = {"$regex": str(source), "$options": "i"}
        if language:
            filters["language"] = language
        if search:
            filters["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"authors": {"$regex": search, "$options": "i"}},
            ]

        books_raw = await repo.list_books(skip=skip, limit=page_size, filters=filters)
        total = await repo.count(filters=filters)

        # ✅ بدون تبدیل دستی id/_id — مستقیم مدل پاسخ سازگار با alias
        books = [BookResponse(**dict(book)) for book in books_raw]

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        logger.info("books_list_ok", total=total, page=page, total_pages=total_pages)
        return {
            "items": books,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    except Exception as e:
        logger.error("books_list_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch books: {str(e)}",
        )

# --------------------------------------------------------------------
@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: str,
    repo: BookRepository = Depends(get_book_repository),
) -> BookResponse:
    """Get a book document by MongoDB ObjectId."""
    logger.info("book_get_requested", book_id=book_id)

    try:
        book = await repo.get_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        return BookResponse(**dict(book))

    except HTTPException:
        raise
    except Exception as e:
        logger.error("book_get_failed", book_id=book_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch book: {str(e)}",
        )

# --------------------------------------------------------------------
@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    request: BookCreate,
    repo: BookRepository = Depends(get_book_repository),
) -> BookResponse:
    """Create a new book entry in MongoDB."""
    logger.info("book_create_requested", title=request.title)

    try:
        book_data = request.model_dump(exclude_unset=True)
        created_book = await repo.create(book_data)
        response = BookResponse(**dict(created_book))  # ✅ alias-aware
        logger.info("book_created_successfully", book_id=response.id)
        return response

    except DuplicateBookError as e:
        logger.warning("duplicate_book_creation", isbn=request.isbn)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    except Exception as e:
        logger.error("book_create_failed", title=request.title, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create book: {str(e)}")

# --------------------------------------------------------------------
@router.put("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: str,
    request: BookUpdate,
    repo: BookRepository = Depends(get_book_repository),
) -> BookResponse:
    """Update an existing book document in MongoDB."""
    logger.info("book_update_requested", book_id=book_id)

    try:
        update_data = request.model_dump(exclude_unset=True)
        updated_book = await repo.update(book_id, update_data)
        return BookResponse(**dict(updated_book))

    except BookNotFoundError:
        logger.warning("book_not_found_for_update", book_id=book_id)
        raise HTTPException(status_code=404, detail="Book not found")

    except Exception as e:
        logger.error("book_update_failed", book_id=book_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update book: {str(e)}",
        )

# --------------------------------------------------------------------
@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: str,
    repo: BookRepository = Depends(get_book_repository),
) -> None:
    """Permanently delete a book document from MongoDB."""
    logger.info("book_delete_requested", book_id=book_id)

    try:
        success = await repo.delete(book_id)
        if not success:
            raise HTTPException(status_code=404, detail="Book not found")
        logger.info("book_deleted", book_id=book_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("book_delete_failed", book_id=book_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete book: {str(e)}",
        )

# --------------------------------------------------------------------
@router.get("/isbn/{isbn}", response_model=BookResponse)
async def get_book_by_isbn(
    isbn: str,
    repo: BookRepository = Depends(get_book_repository),
) -> BookResponse:
    """Retrieve a book document by its ISBN."""
    logger.info("book_by_isbn_requested", isbn=isbn)

    try:
        book = await repo.get_by_isbn(isbn)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        return BookResponse(**dict(book))

    except HTTPException:
        raise
    except Exception as e:
        logger.error("book_by_isbn_failed", isbn=isbn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch book: {str(e)}",
        )
