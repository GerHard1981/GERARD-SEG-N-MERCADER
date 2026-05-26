from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.music_library import library_summary, list_audio_files, read_audio_tags

router = APIRouter(prefix="/api/music", tags=["music"])


@router.get("/summary")
def summary() -> dict:
    return library_summary()


@router.get("/files")
def files(limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0), contains: str = "") -> dict:
    return list_audio_files(limit=limit, offset=offset, contains=contains)


@router.get("/tags")
def tags(path: str) -> dict:
    return read_audio_tags(path)
