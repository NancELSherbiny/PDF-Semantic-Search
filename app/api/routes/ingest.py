"""
/ingest/ route — thin: validate the input, then delegate to IngestionService.

Per the API contract, `input` may be one or more PDF files or a directory-path
string (e.g. "/data"). String paths are restricted to INGEST_BASE_DIR. The older
`path` form field is kept as an alias for the string form.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional, Union

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import WithJsonSchema

from app.api.deps import get_ingestion_service
from app.api.schemas.ingest import IngestResponse
from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.services.ingestion_service import IngestionService

router = APIRouter()

# Accepts a file or a path string at runtime, but is documented as a file so
# Swagger UI renders a file picker instead of a pre-filled "string" text box.
FileOrPath = Annotated[Union[UploadFile, str], WithJsonSchema({"type": "string", "format": "binary"})]


@router.post("/ingest/", response_model=IngestResponse)
async def ingest(
    input: Optional[list[FileOrPath]] = File(
        default=None, description="PDF file(s), or a directory path such as /data"
    ),
    path: Optional[str] = Form(default=None, description="Alias for a directory-path input"),
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestResponse:
    documents: list[tuple[str, bytes]] = []
    for item in input or []:
        if isinstance(item, str):
            if item.strip():  # ignore empty form values some clients send
                documents.extend(_read_path(item.strip()))
            continue
        name = item.filename or ""
        if not name.lower().endswith(".pdf"):
            raise BadRequestError("Only PDF files are accepted.")
        documents.append((name, await item.read()))
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
    # Restrict directory ingestion to a configured base dir (default /data) so a
    # caller can't read arbitrary files off the server.
    base = Path(get_settings().ingest_base_dir).resolve()
    path = Path(path_str).resolve()
    if not path.is_relative_to(base):
        raise BadRequestError(f"Path must be inside '{base}'.")
    if path.is_dir():
        pdfs = sorted(path.glob("*.pdf"))
        if not pdfs:
            raise BadRequestError(f"No PDF files found in '{path_str}'.")
        return [(p.name, p.read_bytes()) for p in pdfs]
    if path.is_file() and path.suffix.lower() == ".pdf":
        return [(path.name, path.read_bytes())]
    raise BadRequestError(f"Invalid input path: '{path_str}'.")
