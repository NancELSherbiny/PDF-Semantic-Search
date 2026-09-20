from fastapi.testclient import TestClient

from app.api.deps import get_ingestion_service, get_search_service
from app.main import create_app


class FakeSearchService:
    async def search(self, query, top_k=None):
        return [{"document": "a.pdf", "score": 0.9, "content": "hello"}]


class FakeIngestionService:
    async def ingest_documents(self, documents):
        return [name for name, _ in documents]


def _client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: FakeSearchService()
    app.dependency_overrides[get_ingestion_service] = lambda: FakeIngestionService()
    return TestClient(app)


def test_health():
    r = _client().get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_search_rejects_empty_query():
    r = _client().post("/search/", json={"query": "   "})
    assert r.status_code == 400
    assert r.json() == {"error": "Query cannot be empty."}


def test_search_returns_results():
    r = _client().post("/search/", json={"query": "how does ai learn"})
    assert r.status_code == 200
    assert r.json()["results"][0]["document"] == "a.pdf"


def test_ingest_rejects_non_pdf():
    r = _client().post("/ingest/", files={"input": ("notes.txt", b"hi", "text/plain")})
    assert r.status_code == 400
    assert r.json() == {"error": "Only PDF files are accepted."}


def test_ingest_accepts_pdf():
    r = _client().post("/ingest/", files={"input": ("sample.pdf", b"some text", "application/pdf")})
    assert r.status_code == 200
    body = r.json()
    assert body["files"] == ["sample.pdf"]
    assert "Successfully ingested 1" in body["message"]


def test_ingest_ignores_path_when_file_present():
    # Swagger fills the optional path field with "string"; a real upload must win.
    r = _client().post(
        "/ingest/",
        data={"path": "string"},
        files={"input": ("sample.pdf", b"some text", "application/pdf")},
    )
    assert r.status_code == 200
    assert r.json()["files"] == ["sample.pdf"]
