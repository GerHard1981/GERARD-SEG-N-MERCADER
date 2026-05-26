from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_root_serves_html(client: TestClient) -> None:
    res = client.get("/")
    assert res.status_code == 200
    assert "<title>MusicBox</title>" in res.text
    assert "text/html" in res.headers["content-type"]


def test_health_reports_discogs_cache_and_matches(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["discogs"]["token_configured"] is False
    assert body["discogs"]["base_url"].startswith("http")
    assert "bytes" in body["cache"]
    assert "count" in body["matches"]


def test_library_degrades_without_index(client: TestClient) -> None:
    res = client.get("/api/music/library?limit=10")
    assert res.status_code == 200
    body = res.json()
    assert body["indexed"] is False
    assert body["total"] == 0
    assert res.headers.get("X-Total-Count") == "0"


def test_files_pagination_exposes_total_count(client: TestClient) -> None:
    res = client.get("/api/music/files?limit=5")
    assert res.status_code == 200
    body = res.json()
    assert "total" in body
    assert body["returned"] == len(body["files"])
    assert res.headers.get("X-Total-Count") == str(body["total"])


def test_files_limit_is_capped(client: TestClient) -> None:
    res = client.get("/api/music/files?limit=99999")
    assert res.status_code == 422


def test_discogs_config(client: TestClient) -> None:
    res = client.get("/api/discogs/config")
    assert res.status_code == 200
    assert res.json()["token_configured"] is False


def test_root_route_replaces_cabin(client: TestClient) -> None:
    paths = app.openapi()["paths"]
    assert "/" in paths
    assert "/cabin" not in paths
