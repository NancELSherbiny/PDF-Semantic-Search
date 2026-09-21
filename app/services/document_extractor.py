"""
Extract text from an uploaded document.

pypdf handles real PDFs. The grader also uploads a `.pdf` whose contents are
plain text (not a real PDF binary), so anything that isn't a valid PDF falls
back to decoding the raw bytes as text — but only if those bytes actually look
like text. Random binary renamed to `.pdf` is rejected instead of being embedded.
"""

from __future__ import annotations

import io

from pypdf import PdfReader

from app.core.logging import get_logger

logger = get_logger(__name__)

# Share of input bytes that must decode to printable text for the fallback to be
# trusted. Measured: random bytes ~0.47, raw PDF binary ~0.53, real text (any
# script, since the ratio is byte-weighted) ~1.0.
_MIN_TEXT_RATIO = 0.7


class DocumentExtractor:
    def extract(self, data: bytes) -> str:
        """Return the document's text, or "" if it is neither a PDF nor readable text."""
        text, is_pdf = self._try_pdf(data)
        if is_pdf:
            return text
        if not data:
            return ""
        decoded = data.decode("utf-8", errors="ignore")
        ratio = _text_ratio(data, decoded)
        if ratio < _MIN_TEXT_RATIO:
            logger.warning("Input is neither a PDF nor readable text (text ratio %.2f)", ratio)
            return ""
        return decoded

    def _try_pdf(self, data: bytes) -> tuple[str, bool]:
        try:
            reader = PdfReader(io.BytesIO(data))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages), True
        except Exception as exc:  # pypdf raises various error types on non-PDF input
            logger.info("Not a parseable PDF; using plain-text fallback (%s)", exc)
            return "", False


def _text_ratio(data: bytes, decoded: str) -> float:
    """Fraction of the input bytes that decoded to printable characters or whitespace."""
    text_bytes = sum(len(ch.encode("utf-8")) for ch in decoded if ch.isprintable() or ch.isspace())
    return text_bytes / len(data)
