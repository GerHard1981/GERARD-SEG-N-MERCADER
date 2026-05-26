from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.connectors.discogs_client import discogs_client
from app.services.matcher import match_file, match_folder

router = APIRouter(prefix="/api/discogs", tags=["discogs"])


class MatchFileRequest(BaseModel):
    path: str = Field(..., description="Ruta local del archivo de audio")


class MatchFolderRequest(BaseModel):
    folder: str = Field(..., description="Ruta local de carpeta con audio")
    limit: int = Field(25, ge=1, le=500)


@router.get("/config")
def config() -> dict:
    return discogs_client.config_status()


@router.get("/me")
def me() -> dict:
    return discogs_client.identity()


@router.get("/search")
def search(
    q: str = "",
    type: str = Query("release", description="release, master, artist, label"),
    artist: str = "",
    release_title: str = "",
    track: str = "",
    label: str = "",
    catno: str = "",
    barcode: str = "",
    year: str = "",
    genre: str = "",
    style: str = "",
    format: str = "",
    country: str = "",
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
) -> dict:
    params = {
        "q": q,
        "type": type,
        "artist": artist,
        "release_title": release_title,
        "track": track,
        "label": label,
        "catno": catno,
        "barcode": barcode,
        "year": year,
        "genre": genre,
        "style": style,
        "format": format,
        "country": country,
        "page": page,
        "per_page": per_page,
    }
    return discogs_client.search(**params)


@router.get("/releases/{release_id}")
def release(release_id: int) -> dict:
    return discogs_client.release(release_id)


@router.get("/masters/{master_id}")
def master(master_id: int) -> dict:
    return discogs_client.master(master_id)


@router.get("/artists/{artist_id}")
def artist(artist_id: int) -> dict:
    return discogs_client.artist(artist_id)


@router.get("/labels/{label_id}")
def label(label_id: int) -> dict:
    return discogs_client.label(label_id)


@router.get("/collection/{username}/folders")
def collection_folders(username: str) -> dict:
    return discogs_client.collection_folders(username)


@router.get("/collection/{username}/folder/{folder_id}/releases")
def collection_releases(username: str, folder_id: int = 0, page: int = 1, per_page: int = 50) -> dict:
    return discogs_client.collection_releases(username=username, folder_id=folder_id, page=page, per_page=per_page)


@router.get("/wants/{username}")
def wants(username: str, page: int = 1, per_page: int = 50) -> dict:
    return discogs_client.wants(username=username, page=page, per_page=per_page)


@router.post("/match-file")
def match_file_endpoint(payload: MatchFileRequest) -> dict:
    return match_file(payload.path)


@router.post("/match-folder")
def match_folder_endpoint(payload: MatchFolderRequest) -> dict:
    return match_folder(payload.folder, limit=payload.limit)
