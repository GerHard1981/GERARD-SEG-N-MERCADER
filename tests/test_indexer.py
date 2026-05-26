from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

import app.cabin as cabin
from app.main import app
from app.services.indexer import build_index, is_excluded


def _make_library(root: Path) -> None:
    (root / "Artist" / "Album").mkdir(parents=True)
    (root / "Artist" / "Album" / "song1.mp3").write_bytes(b"not really audio")
    (root / "Artist" / "Album" / "song2.flac").write_bytes(b"not really audio")
    (root / "Artist" / "notes.txt").write_text("ignore me")


def test_build_index_creates_schema_and_counts_audio(tmp_path: Path) -> None:
    music = tmp_path / "music"
    music.mkdir()
    _make_library(music)
    db = tmp_path / "index" / "music_inventory.sqlite3"

    stats = build_index(roots=[music], db_path=db)

    assert stats["indexed"] is True
    assert stats["total"] == 2  # solo los dos archivos de audio
    assert stats["by_extension"] == {".mp3": 1, ".flac": 1}
    assert db.exists()

    with sqlite3.connect(db) as con:
        cols = {row[1] for row in con.execute("PRAGMA table_info(tracks)")}
        count = con.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
    assert count == 2
    assert {"full_path", "artist", "title", "album", "duration_seconds", "bitrate"} <= cols


def test_build_index_is_idempotent(tmp_path: Path) -> None:
    music = tmp_path / "music"
    music.mkdir()
    _make_library(music)
    db = tmp_path / "music_inventory.sqlite3"

    build_index(roots=[music], db_path=db)
    stats = build_index(roots=[music], db_path=db)  # segunda pasada

    with sqlite3.connect(db) as con:
        count = con.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
    assert count == 2  # INSERT OR REPLACE por ruta, no duplica
    assert stats["total"] == 2


def test_build_index_skips_missing_roots(tmp_path: Path) -> None:
    db = tmp_path / "music_inventory.sqlite3"
    stats = build_index(roots=[tmp_path / "no-existe"], db_path=db)
    assert stats["total"] == 0
    assert stats["scanned_roots"] == []
    assert len(stats["skipped_roots"]) == 1


def test_is_excluded() -> None:
    assert is_excluded(Path("/home/user/MUSIC_BOX/app/x.mp3"))
    assert is_excluded(Path("/data/.venv/lib/x.mp3"))
    assert not is_excluded(Path("/home/user/Music/Artist/song.mp3"))


def test_library_endpoint_reads_built_index(tmp_path: Path, monkeypatch) -> None:
    music = tmp_path / "music"
    music.mkdir()
    _make_library(music)
    db = tmp_path / "music_inventory.sqlite3"
    build_index(roots=[music], db_path=db)

    monkeypatch.setattr(cabin, "LIBRARY_DB", db)
    client = TestClient(app)
    res = client.get("/api/music/library?limit=10")

    assert res.status_code == 200
    body = res.json()
    assert body["indexed"] is True
    assert body["total"] == 2
    assert len(body["tracks"]) == 2
    assert res.headers.get("X-Total-Count") == "2"


def test_reindex_endpoint_returns_stats(tmp_path: Path, monkeypatch) -> None:
    import app.services.indexer as indexer

    music = tmp_path / "music"
    music.mkdir()
    _make_library(music)
    db = tmp_path / "music_inventory.sqlite3"
    # Aislar del índice real por defecto para no afectar a otros tests.
    monkeypatch.setattr(indexer, "index_db_path", lambda: db)
    monkeypatch.setattr(indexer, "default_scan_roots", lambda: [music])

    client = TestClient(app)
    res = client.post("/api/music/reindex")
    assert res.status_code == 200
    body = res.json()
    assert body["indexed"] is True
    assert body["total"] == 2
    assert body["db_path"] == str(db)
