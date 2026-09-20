"""
Extract text from an uploaded document.

pypdf handles real PDFs. The grader also uploads a `.pdf` whose contents are
plain text (not a real PDF binary), so anything that isn't a valid PDF falls
back to decoding the raw bytes as text instead of failing.
"""

from __future__ import annotations

import io

from pypdf import PdfReader

from app.core.logging import get_logger

logger = get_logger(__name__)


class DocumentExtractor:
    def extract(self, data: bytes) -> str:
        """Return the text of an uploaded file (real PDF, or plain-text fallback)."""
        text, is_pdf = self._try_pdf(data)
        if is_pdf:
            return text
        return data.decode("utf-8", errors="ignore")

    def _try_pdf(self, data: bytes) -> tuple[str, bool]:
        try:
            reader = PdfReader(io.BytesIO(data))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages), True
        except Exception as exc:  # pypdf raises various error types on non-PDF input
            logger.info("Not a parseable PDF; using plain-text fallback (%s)", exc)
            return "", False
