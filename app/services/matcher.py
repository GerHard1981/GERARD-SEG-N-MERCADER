from __future__ import annotations

import difflib
import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.connectors.discogs_client import discogs_client
from app.services.music_library import iter_audio_files, read_audio_tags

_MATCH_COLUMNS = (
    "id, created_at, file_path, artist, album, title, query, "
    "top_release_id, top_title, top_year, top_uri, score, score_note"
)


def _init_db() -> None:
    settings.matches_db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(settings.matches_db) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS discogs_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at REAL NOT NULL,
                file_path TEXT NOT NULL,
                artist TEXT,
                album TEXT,
                title TEXT,
                query TEXT NOT NULL,
                top_release_id INTEGER,
                top_title TEXT,
                top_year INTEGER,
                top_uri TEXT,
                score REAL,
                score_note TEXT,
                response_json TEXT NOT NULL
            )
            """
        )
        # Migración para bases creadas antes de añadir la columna score.
        cols = {row[1] for row in con.execute("PRAGMA table_info(discogs_matches)")}
        if "score" not in cols:
            con.execute("ALTER TABLE discogs_matches ADD COLUMN score REAL")
        con.execute("CREATE INDEX IF NOT EXISTS idx_match_file ON discogs_matches(file_path)")
        con.commit()


def _norm(value: Any) -> str:
    text = str(value or "").lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def score_match(tags: Dict[str, Any], top: Dict[str, Any]) -> tuple[float, str]:
    """Puntúa la confianza del match (0..1) comparando tags vs título de Discogs.

    Devuelve (score, etiqueta) donde etiqueta ∈ {no_result, weak, likely, strong}.
    """
    if not top:
        return 0.0, "no_result"
    result_title = _norm(top.get("title"))
    artist = _norm(tags.get("artist"))
    album = _norm(tags.get("album"))
    title = _norm(tags.get("title"))
    query = " ".join(part for part in [artist, album or title] if part).strip()
    if not query or not result_title:
        return 0.0, "weak"

    ratio = difflib.SequenceMatcher(None, query, result_title).ratio()
    artist_hit = bool(artist) and all(token in result_title for token in artist.split())
    score = min(1.0, ratio + 0.1) if artist_hit else ratio
    score = round(score, 3)

    if score >= 0.8:
        label = "strong"
    elif score >= 0.55:
        label = "likely"
    else:
        label = "weak"
    return score, label


def save_match(file_path: str, tags: Dict[str, Any], params: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
    _init_db()
    results = ((response.get("data") or {}).get("results") or []) if isinstance(response.get("data"), dict) else []
    top = results[0] if results else {}
    score, label = score_match(tags, top)
    with sqlite3.connect(settings.matches_db) as con:
        con.execute(
            """
            INSERT INTO discogs_matches
            (created_at, file_path, artist, album, title, query, top_release_id, top_title, top_year, top_uri, score, score_note, response_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                time.time(),
                file_path,
                tags.get("artist"),
                tags.get("album"),
                tags.get("title"),
                params.get("q", ""),
                top.get("id"),
                top.get("title"),
                top.get("year"),
                top.get("uri"),
                score,
                label,
                json.dumps(response, ensure_ascii=False),
            ),
        )
        con.commit()
    return {"top_result": top, "score": score, "score_note": label, "matches_db": str(settings.matches_db)}


def _row_to_match(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "file_path": row["file_path"],
        "artist": row["artist"],
        "album": row["album"],
        "title": row["title"],
        "query": row["query"],
        "top_release_id": row["top_release_id"],
        "top_title": row["top_title"],
        "top_year": row["top_year"],
        "top_uri": row["top_uri"],
        "score": row["score"],
        "score_note": row["score_note"],
        "verified": row["score_note"] == "verified_by_user",
    }


def get_matches_for_file(file_path: str, limit: int = 5) -> List[Dict[str, Any]]:
    _init_db()
    with sqlite3.connect(settings.matches_db) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            f"SELECT {_MATCH_COLUMNS} FROM discogs_matches WHERE file_path=? ORDER BY created_at DESC LIMIT ?",
            (file_path, limit),
        ).fetchall()
    return [_row_to_match(row) for row in rows]


def list_recent_matches(limit: int = 50) -> List[Dict[str, Any]]:
    _init_db()
    with sqlite3.connect(settings.matches_db) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            f"SELECT {_MATCH_COLUMNS} FROM discogs_matches ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_match(row) for row in rows]


def verify_match(match_id: int) -> Optional[Dict[str, Any]]:
    _init_db()
    with sqlite3.connect(settings.matches_db) as con:
        con.row_factory = sqlite3.Row
        cur = con.execute(
            "UPDATE discogs_matches SET score=1.0, score_note='verified_by_user' WHERE id=?",
            (match_id,),
        )
        con.commit()
        if cur.rowcount == 0:
            return None
        row = con.execute(
            f"SELECT {_MATCH_COLUMNS} FROM discogs_matches WHERE id=?", (match_id,)
        ).fetchone()
    return _row_to_match(row)


def match_file(path: str) -> Dict[str, Any]:
    tags = read_audio_tags(path)
    params = build_query(tags)
    response = discogs_client.search(**params)
    saved = save_match(path, tags, params, response)
    return {
        "file": path,
        "tags": tags,
        "discogs_query": params,
        "discogs_response": response,
        "saved": saved,
    }


def build_query(tags: Dict[str, Any]) -> Dict[str, Any]:
    artist = (tags.get("artist") or "").strip() if isinstance(tags.get("artist"), str) else ""
    album = (tags.get("album") or "").strip() if isinstance(tags.get("album"), str) else ""
    title = (tags.get("title") or "").strip() if isinstance(tags.get("title"), str) else ""

    if artist and album:
        q = f"{artist} {album}"
    elif artist and title:
        q = f"{artist} {title}"
    else:
        q = title or Path(str(tags.get("path", ""))).stem

    params = {"q": q, "type": "release", "per_page": 5, "page": 1}
    if artist:
        params["artist"] = artist
    return params


def match_folder(folder: str, limit: int = 25) -> Dict[str, Any]:
    root = Path(folder)
    if not root.exists():
        return {"error": f"Folder does not exist: {folder}", "folder": folder}
    matched: List[Dict[str, Any]] = []
    for path in iter_audio_files(root):
        if len(matched) >= limit:
            break
        try:
            item = match_file(str(path))
            saved = item.get("saved", {})
            top = saved.get("top_result") or {}
            matched.append({
                "file": str(path),
                "query": item.get("discogs_query"),
                "score": saved.get("score"),
                "score_note": saved.get("score_note"),
                "top_result": {
                    "id": top.get("id"),
                    "title": top.get("title"),
                    "year": top.get("year"),
                    "uri": top.get("uri"),
                } if top else None,
            })
        except Exception as exc:
            matched.append({"file": str(path), "error": str(exc)})
    return {"folder": folder, "limit": limit, "matched": len(matched), "items": matched, "matches_db": str(settings.matches_db)}
