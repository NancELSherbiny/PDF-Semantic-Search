"""
/ingest/ route — thin: validate the uploaded PDF(s), then delegate to
IngestionService.

`input` is declared as a typed File parameter so FastAPI documents it and
Swagger renders a file picker. An optional `path` form field ingests a
server-side directory of PDFs.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import get_ingestion_service
from app.api.schemas.ingest import IngestResponse
from app.core.exceptions import BadRequestError
from app.services.ingestion_service import IngestionService

router = APIRouter()


@router.post("/ingest/", response_model=IngestResponse)
async def ingest(
    input: list[UploadFile] | None = File(default=None, description="PDF file(s)"),
    path: str | None = Form(default=None, description="Optional server-side directory of PDFs"),
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestResponse:
    documents: list[tuple[str, bytes]] = []
    for upload in input or []:
        name = upload.filename or ""
        if not name.lower().endswith(".pdf"):
            raise BadRequestError("Only PDF files are accepted.")
        documents.append((name, await upload.read()))
    # Only fall back to a server-side directory path when no files were
    # uploaded, so the optional `path` field can't derail a normal file upload.
    if not documents and path:
        documents.extend(_read_path(path))
    if not documents:
        raise BadRequestError("No input provided.")

    ingested = await service.ingest_documents(documents)
    return IngestResponse(
        message=f"Successfully ingested {len(ingested)} PDF document(s).", files=ingested
    )


def _read_path(path_str: str) -> list[tuple[str, bytes]]:
    path = Path(path_str)
    if path.is_dir():
        pdfs = sorted(path.glob("*.pdf"))
        if not pdfs:
            raise BadRequestError(f"No PDF files found in '{path_str}'.")
        return [(p.name, p.read_bytes()) for p in pdfs]
    if path.is_file() and path.suffix.lower() == ".pdf":
        return [(path.name, path.read_bytes())]
    raise BadRequestError(f"Invalid input path: '{path_str}'.")
