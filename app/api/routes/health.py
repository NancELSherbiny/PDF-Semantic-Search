"""Liveness / banner routes."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def root() -> dict:
    return {"message": "PDF Semantic Search API", "docs": "/docs"}


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}
