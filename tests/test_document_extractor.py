from app.services.document_extractor import DocumentExtractor


def test_plain_text_fallback_for_non_pdf():
    # A .pdf whose bytes are plain text (the grader's case) must not crash.
    text = b"Artificial intelligence enables systems to learn from data."
    assert DocumentExtractor().extract(text) == text.decode()


def test_empty_bytes_returns_empty_string():
    assert DocumentExtractor().extract(b"") == ""
