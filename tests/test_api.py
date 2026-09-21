import random

from fastapi.testclient import TestClient

from app.api.deps import get_ingestion_service, get_search_service
from app.core.config import Settings, get_settings
from app.infrastructure.cache.no_op_cache import NoOpCache
from app.main import create_app
from app.services.chunking_service import ChunkingService
from app.services.document_extractor import DocumentExtractor
from app.services.ingestion_service import IngestionService


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


def test_ingest_accepts_directory_path_in_input(tmp_path, monkeypatch):
    # The contract allows `input` to be a directory path string (e.g. /data).
    (tmp_path / "doc.pdf").write_bytes(b"some text")
    monkeypatch.setattr(get_settings(), "ingest_base_dir", str(tmp_path))
    r = _client().post("/ingest/", files={"input": (None, str(tmp_path))})
    assert r.status_code == 200
    assert r.json()["files"] == ["doc.pdf"]


def test_openapi_documents_input_as_file_upload():
    # Keeps Swagger's file picker even though `input` also accepts a path string.
    body = create_app().openapi()["components"]["schemas"]["Body_ingest_ingest__post"]
    assert body["properties"]["input"]["anyOf"][0]["items"] == {"type": "string", "format": "binary"}


def test_ingest_rejects_directory_path_outside_base():
    r = _client().post("/ingest/", files={"input": (None, "/etc")})
    assert r.status_code == 400
    assert "must be inside" in r.json()["error"]


class RecordingStore:
    def __init__(self):
        self.upserts = []

    def upsert(self, document, chunks, vectors):
        self.upserts.append(document)
        return len(chunks)


class FakeEmbedder:
    def embed(self, texts):
        return [[0.0] for _ in texts]


def _client_with_real_ingestion(store) -> TestClient:
    # Real extractor/chunker/ingestion logic; only the model and Qdrant are faked.
    service = IngestionService(
        DocumentExtractor(), ChunkingService(Settings()), FakeEmbedder(), store, NoOpCache()
    )
    app = create_app()
    app.dependency_overrides[get_ingestion_service] = lambda: service
    return TestClient(app)


def test_ingest_is_all_or_nothing_across_files():
    store = RecordingStore()
    r = _client_with_real_ingestion(store).post(
        "/ingest/",
        files=[
            ("input", ("good.pdf", b"valid text content", "application/pdf")),
            ("input", ("empty.pdf", b"", "application/pdf")),
        ],
    )
    assert r.status_code == 400
    assert store.upserts == []  # good.pdf was not indexed


def test_ingest_rejects_binary_garbage_pdf():
    store = RecordingStore()
    garbage = random.Random(0).randbytes(2048)
    r = _client_with_real_ingestion(store).post(
        "/ingest/", files={"input": ("garbage.pdf", garbage, "application/pdf")}
    )
    assert r.status_code == 400
    assert store.upserts == []


def test_ingest_ignores_path_when_file_present():
    # Swagger fills the optional path field with "string"; a real upload must win.
    r = _client().post(
        "/ingest/",
        data={"path": "string"},
        files={"input": ("sample.pdf", b"some text", "application/pdf")},
    )
    assert r.status_code == 200
    assert r.json()["files"] == ["sample.pdf"]
