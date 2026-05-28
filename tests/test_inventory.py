from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

import app.services.indexer as indexer
from app.core.config import parse_music_roots, settings
from app.main import app


# ---------- Multi-ruta ----------

def test_parse_music_roots_multi_and_dedup() -> None:
    fb = Path("/fallback")
    roots = parse_music_roots(" /a ; /b ; /a ;", fb)  # espacios + duplicado
    assert roots == [Path("/a"), Path("/b")]


def test_parse_music_roots_empty_uses_fallback() -> None:
    fb = Path("/fallback")
    assert parse_music_roots("", fb) == [fb]
    assert parse_music_roots("   ", fb) == [fb]


def test_default_scan_roots_falls_back_to_music_master() -> None:
    # Sin MUSIC_ROOTS configurado (entorno de test) -> raíz única music_master.
    assert indexer.default_scan_roots() == [settings.music_master]


# ---------- WAL ----------

def test_init_db_enables_wal(tmp_path: Path) -> None:
    db = tmp_path / "idx.sqlite3"
    conn = indexer.init_db(db)
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        conn.close()
    assert mode == "wal"


# ---------- Helpers ----------

def _audio(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _insert(db: Path, full_path: str, *, artist: str = "", album: str = "", title: str = "",
            sha: str = "", root: str = "/r1") -> None:
    with sqlite3.connect(db) as con:
        con.execute(
            "INSERT INTO tracks (full_path, filename, extension, size_bytes, root_source,"
            " artist, album, title, sha256, indexed_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (full_path, Path(full_path).name, ".mp3", 1, root, artist, album, title, sha,
             "2026-01-01T00:00:00"),
        )
        con.commit()


# ---------- sha256 + dedup por hash (vía build_index) ----------

def test_build_index_stores_sha256_and_flags_hash_duplicates(tmp_path: Path) -> None:
    music = tmp_path / "music"
    _audio(music / "a.mp3", b"IDENTICAL-AUDIO-BYTES")
    _audio(music / "b.mp3", b"IDENTICAL-AUDIO-BYTES")  # mismo contenido -> mismo hash
    _audio(music / "c.flac", b"contenido distinto")
    db = tmp_path / "idx.sqlite3"

    stats = indexer.build_index(roots=[music], db_path=db)
    assert stats["total"] == 3

    inv = indexer.query_inventory(db_path=db, limit=100)
    assert inv["total"] == 3
    by = {it["filename"]: it for it in inv["items"]}

    assert by["a.mp3"]["sha256"] == hashlib.sha256(b"IDENTICAL-AUDIO-BYTES").hexdigest()
    assert by["a.mp3"]["sha256"] == by["b.mp3"]["sha256"]
    assert by["a.mp3"]["duplicate_by_hash"] is True
    assert by["b.mp3"]["duplicate"] is True
    assert by["c.flac"]["duplicate"] is False

    dup = indexer.query_inventory(db_path=db, status="duplicated")
    assert {i["filename"] for i in dup["items"]} == {"a.mp3", "b.mp3"}
    uniq = indexer.query_inventory(db_path=db, status="unique")
    assert {i["filename"] for i in uniq["items"]} == {"c.flac"}


# ---------- dedup por metadatos + filtro por fuente ----------

def test_metadata_duplicates_and_source_filter(tmp_path: Path) -> None:
    db = tmp_path / "idx.sqlite3"
    indexer.init_db(db).close()
    # Mismo artista+álbum+título (distinta capitalización/puntuación) y distinto hash -> dup por metadatos.
    _insert(db, "/r1/x1.mp3", artist="Daft Punk", album="Discovery", title="One More Time", sha="h1", root="/r1")
    _insert(db, "/r2/x2.mp3", artist="daft punk", album="discovery", title="ONE  more time!", sha="h2", root="/r2")
    _insert(db, "/r1/x3.mp3", artist="Otro", album="Disco", title="Solo", sha="h3", root="/r1")

    inv = indexer.query_inventory(db_path=db)
    assert inv["total"] == 3
    by = {i["filename"]: i for i in inv["items"]}
    assert by["x1.mp3"]["duplicate_by_metadata"] is True
    assert by["x2.mp3"]["duplicate_by_metadata"] is True
    assert by["x1.mp3"]["duplicate_by_hash"] is False  # hashes distintos
    assert by["x3.mp3"]["duplicate"] is False
    assert set(inv["sources"]) == {"/r1", "/r2"}

    only_r2 = indexer.query_inventory(db_path=db, source="/r2")
    assert only_r2["total"] == 1
    assert only_r2["items"][0]["filename"] == "x2.mp3"


def test_query_inventory_missing_db(tmp_path: Path) -> None:
    inv = indexer.query_inventory(db_path=tmp_path / "no-existe.sqlite3")
    assert inv["indexed"] is False
    assert inv["total"] == 0


# ---------- Endpoint ----------

def test_inventory_endpoint(tmp_path: Path, monkeypatch) -> None:
    db = tmp_path / "idx.sqlite3"
    indexer.init_db(db).close()
    _insert(db, "/r1/a.mp3", sha="dup", root="/r1")
    _insert(db, "/r2/b.mp3", sha="dup", root="/r2")  # mismo hash -> duplicados
    _insert(db, "/r1/c.mp3", sha="uniq", root="/r1")
    monkeypatch.setattr(indexer, "index_db_path", lambda: db)

    client = TestClient(app)

    res = client.get("/api/music/inventory?limit=10")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 3
    assert res.headers.get("X-Total-Count") == "3"

    dup = client.get("/api/music/inventory?status=duplicated")
    assert dup.json()["total"] == 2
    assert dup.headers.get("X-Total-Count") == "2"

    r2 = client.get("/api/music/inventory?source=/r2")
    assert r2.json()["total"] == 1

    bad = client.get("/api/music/inventory?status=nope")  # Literal -> validación 422
    assert bad.status_code == 422
