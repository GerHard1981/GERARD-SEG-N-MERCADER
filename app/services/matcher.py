from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.connectors.discogs_client import discogs_client
from app.services.music_library import iter_audio_files, read_audio_tags


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
                score_note TEXT,
                response_json TEXT NOT NULL
            )
            """
        )
        con.commit()


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


def save_match(file_path: str, tags: Dict[str, Any], params: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
    _init_db()
    results = ((response.get("data") or {}).get("results") or []) if isinstance(response.get("data"), dict) else []
    top = results[0] if results else {}
    with sqlite3.connect(settings.matches_db) as con:
        con.execute(
            """
            INSERT INTO discogs_matches
            (created_at, file_path, artist, album, title, query, top_release_id, top_title, top_year, top_uri, score_note, response_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                "top_result_unverified" if top else "no_result",
                json.dumps(response, ensure_ascii=False),
            ),
        )
        con.commit()
    return {"top_result": top, "matches_db": str(settings.matches_db)}


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
            top = item.get("saved", {}).get("top_result") or {}
            matched.append({
                "file": str(path),
                "query": item.get("discogs_query"),
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
