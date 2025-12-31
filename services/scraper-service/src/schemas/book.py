"""
Book Schemas
Handles Pydantic models for Book operations in MongoDB
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId


# ─────────────────────────────────────────────
# Custom ObjectId type
# ─────────────────────────────────────────────
class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic v2"""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        # JSON Schema representation for OpenAPI
        return {"type": "string"}


# ─────────────────────────────────────────────
# Base Schema
# ─────────────────────────────────────────────
class BookBase(BaseModel):
    """Base Book Schema (shared by all models)"""

    title: str = Field(..., min_length=1, max_length=500)
    authors: List[str] = Field(default_factory=list)
    isbn: Optional[str] = Field(
        None,
        max_length=17,
        pattern=r"^(97(8|9))?\d{9}(\d|X)?$",
        description="Valid ISBN-10 or ISBN-13 pattern",
    )
    publisher: Optional[str] = Field(None, max_length=200)
    published_date: Optional[str] = None
    language: Optional[str] = Field("fa", max_length=10)
    description: Optional[str] = None
    page_count: Optional[int] = Field(None, ge=0)
    categories: List[str] = Field(default_factory=list)
    cover_url: Optional[str] = None
    source_url: Optional[str] = None


# ─────────────────────────────────────────────
# Book Creation Schema
# ─────────────────────────────────────────────
class BookCreate(BookBase):
    """Schema for book creation request"""
    # explicit for clarity and schema separation
    pass


# ─────────────────────────────────────────────
# Book Update Schema
# ─────────────────────────────────────────────
class BookUpdate(BaseModel):
    """Schema for updating an existing book"""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    authors: Optional[List[str]] = None
    isbn: Optional[str] = Field(
        None,
        max_length=17,
        pattern=r"^(97(8|9))?\d{9}(\d|X)?$",
    )
    publisher: Optional[str] = Field(None, max_length=200)
    published_date: Optional[str] = None
    language: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = None
    page_count: Optional[int] = Field(None, ge=0)
    categories: Optional[List[str]] = None
    cover_url: Optional[str] = None
    source_url: Optional[str] = None


# ─────────────────────────────────────────────
# Book In Database (MongoDB Model)
# ─────────────────────────────────────────────
class BookInDB(BookBase):
    """Schema representing book stored in MongoDB"""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str,
            datetime: lambda v: v.isoformat(),
        },
    }


# ─────────────────────────────────────────────
# Response Schema (for API output)
# ─────────────────────────────────────────────
class BookResponse(BookBase):
    """Schema for book returned to API clients"""

    id: str = Field(..., alias="_id")
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "json_encoders": {
            ObjectId: str,
            datetime: lambda v: v.isoformat(),
        },
    }
