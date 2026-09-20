"""Response schema for /ingest/ (the request is multipart form data)."""

from __future__ import annotations

from pydantic import BaseModel


class IngestResponse(BaseModel):
    message: str
    files: list[str]
