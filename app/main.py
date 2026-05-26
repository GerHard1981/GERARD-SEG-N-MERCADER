from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.health import router as health_router
from app.routers.music import router as music_router
from app.routers.discogs import router as discogs_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="MusicBox app corregida para integrar Discogs: catalogo, releases, masters, artistas, labels y matching de archivos locales.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1", "http://localhost", "http://127.0.0.1:8765", "http://localhost:8765"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(music_router)
app.include_router(discogs_router)

from app.cabin import router as cabin_router
app.include_router(cabin_router)

