from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.services.matcher as matcher
from app.main import app

TOP = {"id": 123, "title": "Daft Punk - Discovery", "year": 2001, "uri": "/release/123"}


def test_score_match_no_result() -> None:
    score, label = matcher.score_match({"artist": "x"}, {})
    assert score == 0.0
    assert label == "no_result"


def test_score_match_strong() -> None:
    score, label = matcher.score_match({"artist": "Daft Punk", "album": "Discovery"}, TOP)
    assert score >= 0.8
    assert label == "strong"


def test_score_match_weak() -> None:
    score, label = matcher.score_match(
        {"artist": "Unrelated", "album": "Something Else"},
        {"title": "Completely Different Record"},
    )
    assert score < 0.55
    assert label == "weak"


def test_save_get_and_verify_match(tmp_path: Path, monkeypatch) -> None:
    db = tmp_path / "matches.sqlite3"
    monkeypatch.setattr(matcher, "settings", SimpleNamespace(matches_db=db))

    saved = matcher.save_match(
        "/music/song.mp3",
        {"artist": "Daft Punk", "album": "Discovery", "title": "One More Time"},
        {"q": "Daft Punk Discovery"},
        {"data": {"results": [TOP]}},
    )
    assert saved["score"] >= 0.8
    assert saved["score_note"] == "strong"

    rows = matcher.get_matches_for_file("/music/song.mp3")
    assert len(rows) == 1
    row = rows[0]
    assert row["top_release_id"] == 123
    assert row["verified"] is False

    verified = matcher.verify_match(row["id"])
    assert verified is not None
    assert verified["verified"] is True
    assert verified["score"] == 1.0

    assert matcher.verify_match(999999) is None


def test_matches_endpoints(tmp_path: Path, monkeypatch) -> None:
    db = tmp_path / "matches.sqlite3"
    monkeypatch.setattr(matcher, "settings", SimpleNamespace(matches_db=db))
    matcher.save_match(
        "/music/song.mp3",
        {"artist": "Daft Punk", "album": "Discovery"},
        {"q": "Daft Punk Discovery"},
        {"data": {"results": [TOP]}},
    )

    client = TestClient(app)

    res = client.get("/api/discogs/matches", params={"path": "/music/song.mp3"})
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 1
    match_id = body["matches"][0]["id"]

    ok = client.post(f"/api/discogs/matches/{match_id}/verify")
    assert ok.status_code == 200
    assert ok.json()["verified"] is True

    missing = client.post("/api/discogs/matches/999999/verify")
    assert missing.status_code == 404
