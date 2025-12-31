"""Book Model"""

from datetime import date
from enum import Enum
from typing import Optional

from sqlalchemy import Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SoftDeleteMixin, TimestampMixin


class BookLanguage(str, Enum):
    """Book language enum"""

    PERSIAN = "fa"
    ENGLISH = "en"
    ARABIC = "ar"
    OTHER = "other"


class BookFormat(str, Enum):
    """Book format enum"""

    PAPERBACK = "paperback"
    HARDCOVER = "hardcover"
    EBOOK = "ebook"
    AUDIOBOOK = "audiobook"


class Book(Base, TimestampMixin, SoftDeleteMixin):
    """Book model"""

    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    subtitle: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    author: Mapped[str] = mapped_column(String(300), nullable=False, index=True)

    isbn: Mapped[Optional[str]] = mapped_column(
        String(13), unique=True, nullable=True, index=True
    )

    publisher: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    publish_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    language: Mapped[BookLanguage] = mapped_column(
        String(10), default=BookLanguage.PERSIAN, index=True
    )

    pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    format: Mapped[Optional[BookFormat]] = mapped_column(String(20), nullable=True)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    cover_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)

    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    source_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)

    source_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
