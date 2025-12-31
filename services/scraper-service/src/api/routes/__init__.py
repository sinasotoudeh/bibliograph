"""
API Routes Package
"""

from fastapi import APIRouter

from .books import router as books_router
from .health import router as health_router
from .scraper import router as scraper_router

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(scraper_router, tags=["Scraping"])
api_router.include_router(books_router, tags=["Books"])

__all__ = ["api_router"]
