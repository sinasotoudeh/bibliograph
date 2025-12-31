"""
Scraper Control Endpoints
-----------------------------------------------------
Handles Celery-based scraping task dispatch, live status monitoring,
and MongoDB statistics aggregation for NLAI source.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from celery.result import AsyncResult

from src.core.database import DatabaseManager
from src.tasks.celery_app import celery_app
from src.tasks.scraping_tasks import scrape_nlai
from src.repositories.book_repo import BookRepository
from src.repositories.scraping_log_repo import ScrapingLogRepository

from ..dependencies import get_db_manager


logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/scraping", tags=["Scraping"])

# ==========================================================
# ============= Request / Response Models ==================
# ==========================================================

class ScrapingStartRequest(BaseModel):
    """Request model for starting a scraping task."""
    source: str = Field(..., description="Source name", examples=["nlai"])
    author_list: List[str] = Field(..., description="List of authors or Range string")
    
    # [CHANGE] max_pages removed, max_results added
    max_results: Optional[int] = Field(
        None, 
        ge=1, 
        description="Skip author if total books exceed this number (Safety Limit)"
    )
    
    force_refresh: bool = Field(False, description="Force full rescraping")

class ScrapingTaskResponse(BaseModel):
    """Response model for initial task dispatch."""
    task_id: str
    source: str
    status: str
    started_at: datetime
    message: str

class ScrapingStatusResponse(BaseModel):
    """Live progress response model."""
    task_id: str
    status: str
    progress: Optional[float] = 0.0
    inserted_count: Optional[int] = 0
    error_count: Optional[int] = 0
    
    # [NEW] Fields for business logic monitoring
    skipped_count: Optional[int] = 0 
    
    current_author: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ScrapingStatsResponse(BaseModel):
    """Aggregated statistics for scraped books."""
    total_books_scraped: int
    sources: Dict[str, Any]


# ==========================================================
# ==================== Endpoints ===========================
# ==========================================================

@router.post("/start", response_model=ScrapingTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_scraping_task(
    request: ScrapingStartRequest,
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> ScrapingTaskResponse:
    
    logger.info("scraper.start", source=request.source, limit=request.max_results)

    if request.source != "nlai":
        raise HTTPException(status_code=400, detail="Invalid source")

    try:
        # [CHANGE] Passing max_results to the task
        task = scrape_nlai.delay(request.author_list, max_results=request.max_results)
        
        return ScrapingTaskResponse(
            task_id=task.id,
            source=request.source,
            status="started",
            started_at=datetime.utcnow(),
            message=f"Task queued. Limit: {request.max_results or 'Unlimited'}",
        )

    except Exception as e:
        logger.error("scraper.start_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}", response_model=ScrapingStatusResponse)
async def get_task_status(task_id: str) -> ScrapingStatusResponse:
    """
    Retrieve live status including skipped counts.
    """
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        meta = task_result.info if isinstance(task_result.info, dict) else {}

        return ScrapingStatusResponse(
            task_id=task_id,
            status=task_result.status,
            progress=float(meta.get("progress", 0.0)),
            inserted_count=meta.get("books_saved", 0),
            error_count=meta.get("books_failed", 0),
            
            # [NEW] Expose skipped count to API
            skipped_count=meta.get("skipped_authors_count", 0),
            
            current_author=meta.get("current_author"),
            started_at=meta.get("started_at"),
            completed_at=datetime.utcnow() if task_result.status == "SUCCESS" else None,
            error_message=str(meta.get("error")) if task_result.status == "FAILURE" else None,
        )

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/stats", response_model=ScrapingStatsResponse)
async def get_scraping_stats(
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> ScrapingStatsResponse:
    """
    Get aggregated scraping statistics using MongoDB only.
    Serves unified data for Grafana / Prometheus dashboards.
    """
    logger.info("scraper.stats_requested")

    try:
        # ──────────────────────────────────────────────
        # ✅ MongoDB - scraping logs (progress & task state)
        from src.repositories.scraping_log_repo import ScrapingLogRepository
        log_repo = ScrapingLogRepository(db_manager.mongodb)
        recent_logs = await log_repo.get_recent_logs(source="nlai", limit=50)

        # Aggregate log statistics
        total_tasks = len(recent_logs)
        completed_tasks = sum(1 for log in recent_logs if log.get("status") == "success")
        failed_tasks = sum(1 for log in recent_logs if log.get("status") == "failed")
        running_tasks = sum(1 for log in recent_logs if log.get("status") == "running")

        # ──────────────────────────────────────────────
        # ✅ MongoDB - raw scraped books
        from src.repositories.book_repo import BookRepository
        book_repo = BookRepository(db_manager.mongodb)
        total_books = await book_repo.count(filters={"source": "nlai"})

        # ──────────────────────────────────────────────
        # ✅ ترکیب داده‌ها برای خروجی نهایی
        stats_payload = {
            "total_tasks": total_tasks,
            "active_tasks": running_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "total_books_scraped": total_books,
            "sources": {
                "nlai": {
                    "scraped": total_books,
                    "last_run": recent_logs[0].get("updated_at").isoformat()
                    if recent_logs else None,
                    "avg_success_rate": None,
                    "avg_duration": None,
                }
            },
        }

        logger.info("scraper.stats_ok", summary=stats_payload)
        return ScrapingStatsResponse(**stats_payload)

    except Exception as e:
        logger.error("scraper.stats_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch scraping stats: {str(e)}",
        )


@router.get("/sources", status_code=status.HTTP_200_OK)
async def list_available_sources() -> Dict[str, Any]:
    """
    List all configured scraping sources (for dashboard UI).
    """
    sources = [
        {
            "name": "nlai",
            "display_name": "Iran National Library & Archives",
            "url": "https://nlai.ir",
            "status": "active",
            "supports_authors": True,
        }
    ]
    return {"sources": sources, "total": len(sources)}
@router.get("/events/{source}")
async def get_recent_scraping_events(
    source: str,
    db_manager: DatabaseManager = Depends(get_db_manager),
):
    """
    Return recent scraping task log events from MongoDB.
    Used by Grafana dashboards.
    """
    repo = ScrapingLogRepository(db_manager.mongodb)
    logs = await repo.get_recent_logs(source)


    return {"source": source, "events": logs}
