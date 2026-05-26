from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


def _file_size(path: Path) -> Optional[int]:
    try:
        return path.stat().st_size if path.exists() else None
    except OSError:
        return None


def _matches_count() -> Optional[int]:
    db = settings.matches_db
    if not db.exists():
        return 0
    try:
        with sqlite3.connect(db) as con:
            return con.execute("SELECT COUNT(*) FROM discogs_matches").fetchone()[0]
    except sqlite3.Error:
        return None


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "google_account": settings.google_account,
        "music_master": str(settings.music_master),
        "music_master_exists": settings.music_master.exists(),
        "musicbox_root": str(settings.musicbox_root),
        "discogs": {
            "token_configured": settings.token_configured,
            "base_url": settings.discogs_api_base,
            "user_agent": settings.discogs_user_agent,
        },
        "cache": {
            "path": str(settings.discogs_cache_db),
            "exists": settings.discogs_cache_db.exists(),
            "bytes": _file_size(settings.discogs_cache_db),
            "ttl_seconds": settings.discogs_cache_ttl_seconds,
        },
        "matches": {
            "path": str(settings.matches_db),
            "exists": settings.matches_db.exists(),
            "count": _matches_count(),
        },
    }
