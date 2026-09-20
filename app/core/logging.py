"""
Logging setup, driven by settings.

Services call `get_logger(__name__)` instead of importing `logging` directly,
so the backend can change in one place without touching business code.
"""

from __future__ import annotations

import logging

from app.core.config import Settings

_configured = False


def configure_logging(settings: Settings) -> None:
    """Configure root logging once, at the level from settings."""
    global _configured
    if _configured:
        return
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
