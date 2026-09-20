from app.core.config import Settings, get_settings


def test_defaults():
    s = Settings()
    assert s.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
    assert s.chunk_size == 180
    assert s.qdrant_host == "qdrant"
    assert s.cache_enabled is False


def test_env_override(monkeypatch):
    monkeypatch.setenv("CHUNK_SIZE", "50")
    monkeypatch.setenv("QDRANT_HOST", "localhost")
    monkeypatch.setenv("CACHE_ENABLED", "true")
    s = Settings()
    assert s.chunk_size == 50
    assert s.qdrant_host == "localhost"
    assert s.cache_enabled is True


def test_get_settings_is_cached():
    assert get_settings() is get_settings()
