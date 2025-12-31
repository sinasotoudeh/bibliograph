"""
Scraping Log ORM Model
---------------------------------------------------------
Models task execution logs and metrics for scraping jobs.
Integrated with Celery task metadata and ScrapingLogRepository.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any

from sqlalchemy import JSON, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class ScrapingStatus(str, Enum):
    """Lifecycle states for a scraping task."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    STOPPED = "stopped"


class ScrapingLog(Base, TimestampMixin):
    """
    ORM entity representing a scraping task lifecycle log.
    Captures progress, counts, durations, and error context.
    """

    __tablename__ = "scraping_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(
        String(50),
        default=ScrapingStatus.PENDING,
        index=True,
    )

    target_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    books_found: Mapped[int] = mapped_column(Integer, default=0)
    books_saved: Mapped[int] = mapped_column(Integer, default=0)
    books_failed: Mapped[int] = mapped_column(Integer, default=0)

    current_author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    progress: Mapped[Optional[float]] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # -------------------- Computed Properties --------------------

    @property
    def duration(self) -> Optional[timedelta]:
        """Compute total duration between start and completion."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    @property
    def success_rate(self) -> float:
        """Compute success percentage of saved items."""
        if self.books_found > 0:
            return round((self.books_saved / self.books_found) * 100, 2)
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize model for JSON response / logging."""
        return {
            "task_id": self.task_id,
            "source": self.source,
            "status": self.status,
            "progress": self.progress,
            "books_found": self.books_found,
            "books_saved": self.books_saved,
            "books_failed": self.books_failed,
            "success_rate": self.success_rate,
            "current_author": self.current_author,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration.total_seconds() if self.duration else None,
            "metadata": self.metadata_,
        }
