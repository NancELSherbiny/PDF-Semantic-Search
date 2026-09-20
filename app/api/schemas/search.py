"""Request/response schemas for /search/."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural-language search query")
    top_k: Optional[int] = Field(default=None, ge=1, le=100, description="Number of results")


class SearchResult(BaseModel):
    document: str
    score: float
    content: str


class SearchResponse(BaseModel):
    results: list[SearchResult]
