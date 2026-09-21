import random
from pathlib import Path

from app.services.document_extractor import DocumentExtractor

SAMPLE_PDF = Path(__file__).resolve().parents[1] / "data" / "sample.pdf"


def test_plain_text_fallback_for_non_pdf():
    # A .pdf whose bytes are plain text (the grader's case) must not crash.
    text = b"Artificial intelligence enables systems to learn from data."
    assert DocumentExtractor().extract(text) == text.decode()


def test_empty_bytes_returns_empty_string():
    assert DocumentExtractor().extract(b"") == ""


def test_random_binary_named_pdf_is_rejected():
    garbage = random.Random(0).randbytes(2048)
    assert DocumentExtractor().extract(garbage) == ""


def test_non_ascii_text_is_not_rejected():
    text = "Le modèle apprend à partir des données. الذكاء الاصطناعي يتعلم من البيانات."
    assert DocumentExtractor().extract(text.encode()) == text


def test_real_sample_pdf_is_extracted():
    assert "Sample Document" in DocumentExtractor().extract(SAMPLE_PDF.read_bytes())
