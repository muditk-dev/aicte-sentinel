import os
import json
import pytest
from httpx import AsyncClient, ASGITransport
from app.core.config import Settings
from app.main import create_application


def test_cors_origins_render_comma_separated(monkeypatch):
    """Verifies that the comma-separated format previously crashing Render parses correctly."""
    raw_env = "https://aicte-sentinel-theta.vercel.app,https://*.vercel.app,http://localhost:5173"
    monkeypatch.setenv("CORS_ORIGINS", raw_env)
    
    settings = Settings()
    assert isinstance(settings.CORS_ORIGINS, list)
    assert "https://aicte-sentinel-theta.vercel.app" in settings.CORS_ORIGINS
    assert "http://localhost:5173" in settings.CORS_ORIGINS
    assert len(settings.CORS_ORIGINS) == 3


def test_cors_origins_json_array(monkeypatch):
    """Verifies that a standard JSON array string in CORS_ORIGINS parses correctly."""
    origins = ["https://aicte-sentinel-theta.vercel.app", "http://localhost:5173"]
    monkeypatch.setenv("CORS_ORIGINS", json.dumps(origins))
    
    settings = Settings()
    assert isinstance(settings.CORS_ORIGINS, list)
    assert settings.CORS_ORIGINS == origins


def test_cors_origins_single_origin(monkeypatch):
    """Verifies that a single origin string without commas or brackets parses cleanly."""
    origin = "https://aicte-sentinel-theta.vercel.app"
    monkeypatch.setenv("CORS_ORIGINS", origin)
    
    settings = Settings()
    assert isinstance(settings.CORS_ORIGINS, list)
    assert settings.CORS_ORIGINS == [origin]


def test_cors_origins_trailing_slashes_stripped(monkeypatch):
    """Verifies that trailing slashes are stripped from origin URLs for accurate CORS matching."""
    raw_env = "https://aicte-sentinel-theta.vercel.app/, http://localhost:5173/"
    monkeypatch.setenv("CORS_ORIGINS", raw_env)
    
    settings = Settings()
    assert settings.CORS_ORIGINS == [
        "https://aicte-sentinel-theta.vercel.app",
        "http://localhost:5173"
    ]


def test_cors_origins_empty_string(monkeypatch):
    """Verifies that empty string or whitespace does not crash and yields empty list."""
    monkeypatch.setenv("CORS_ORIGINS", "   ")
    settings = Settings()
    assert settings.CORS_ORIGINS == []


def test_cors_origins_default_when_unset(monkeypatch):
    """Verifies default origins when environment variable is not set."""
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    settings = Settings()
    assert isinstance(settings.CORS_ORIGINS, list)
    assert "http://localhost:5173" in settings.CORS_ORIGINS
    assert "https://aicte-sentinel-theta.vercel.app" in settings.CORS_ORIGINS


@pytest.mark.asyncio
async def test_cors_middleware_allowed_production_origin():
    """Verifies that production frontend origin receives CORS allow headers."""
    app = create_application()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/health",
            headers={"Origin": "https://aicte-sentinel-theta.vercel.app"}
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "https://aicte-sentinel-theta.vercel.app"
        assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_cors_middleware_allowed_preview_origin():
    """Verifies that Vercel preview branch origins match the origin regex."""
    app = create_application()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        preview_origin = "https://aicte-sentinel-preview-pr12.vercel.app"
        response = await client.get(
            "/api/health",
            headers={"Origin": preview_origin}
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == preview_origin


@pytest.mark.asyncio
async def test_cors_middleware_rejects_disallowed_origin():
    """Verifies that unauthorized origins do not receive CORS allow headers."""
    app = create_application()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/health",
            headers={"Origin": "https://unauthorized-malicious-site.com"}
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers
