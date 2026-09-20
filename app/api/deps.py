"""
Dependency-injection providers.

Services are built once in the app lifespan and stored on app.state; these
providers hand them to routes. Tests override these to inject fakes.
"""

from __future__ import annotations

from fastapi import Request

from app.services.ingestion_service import IngestionService
from app.services.search_service import SearchService


def get_ingestion_service(request: Request) -> IngestionService:
    return request.app.state.ingestion_service


def get_search_service(request: Request) -> SearchService:
    return request.app.state.search_service
