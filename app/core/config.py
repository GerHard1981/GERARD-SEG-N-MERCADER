from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

APP_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = APP_ROOT / ".env"
load_dotenv(ENV_FILE)


def _default_music_master() -> str:
    return str(Path.home() / "Google Drive" / "Music_Master")


def _default_musicbox_root() -> str:
    return str(Path.home() / "Google Drive" / "MUSIC_BOX")


def parse_music_roots(raw: str, fallback: Path) -> List[Path]:
    """Convierte la variable MUSIC_ROOTS (rutas separadas por ';') en una lista de Path.

    Mantiene el orden, elimina duplicados y, si no hay nada configurado, devuelve
    [fallback] para no romper la configuración actual de raíz única.
    """
    roots: List[Path] = []
    seen = set()
    for part in (raw or "").split(";"):
        part = part.strip()
        if not part:
            continue
        path = Path(part)
        key = str(path)
        if key not in seen:
            seen.add(key)
            roots.append(path)
    return roots or [fallback]


@dataclass(frozen=True)
class Settings:
    app_name: str = "MusicBox Discogs API"
    app_version: str = "0.2.0"
    google_account: str = "segunmercader.g@gmail.com"
    app_root: Path = APP_ROOT
    env_file: Path = ENV_FILE
    music_master: Path = Path(os.getenv("MUSIC_MASTER", _default_music_master()))
    musicbox_root: Path = Path(os.getenv("MUSICBOX_ROOT", _default_musicbox_root()))
    music_roots_env: str = os.getenv("MUSIC_ROOTS", "")
    discogs_api_base: str = os.getenv("DISCOGS_API_BASE", "https://api.discogs.com").rstrip("/")
    discogs_token: str = os.getenv("DISCOGS_TOKEN", "").strip()
    discogs_user_agent: str = os.getenv("DISCOGS_USER_AGENT", "MusicBoxDiscogs/0.1 +local").strip()
    discogs_cache_ttl_seconds: int = int(os.getenv("DISCOGS_CACHE_TTL_SECONDS", "604800"))
    api_host: str = os.getenv("MUSICBOX_API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("MUSICBOX_API_PORT", "8765"))

    @property
    def music_roots(self) -> List[Path]:
        """Raíces de música a indexar. Multi-ruta vía MUSIC_ROOTS; si no, music_master."""
        return parse_music_roots(self.music_roots_env, self.music_master)

    @property
    def data_dir(self) -> Path:
        return self.app_root / "data"

    @property
    def discogs_cache_db(self) -> Path:
        return self.data_dir / "discogs_cache.sqlite3"

    @property
    def matches_db(self) -> Path:
        return self.data_dir / "musicbox_discogs_matches.sqlite3"

    @property
    def token_configured(self) -> bool:
        return bool(self.discogs_token)


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.music_master.mkdir(parents=True, exist_ok=True)
settings.musicbox_root.mkdir(parents=True, exist_ok=True)
