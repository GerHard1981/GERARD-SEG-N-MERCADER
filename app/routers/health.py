from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


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
        "discogs_token_configured": settings.token_configured,
    }
