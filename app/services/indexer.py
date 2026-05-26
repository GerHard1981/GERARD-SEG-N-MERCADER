from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from mutagen import File as MutagenFile

from app.core.config import settings

AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aiff", ".aif", ".m4a", ".ogg", ".aac", ".wma", ".opus"}

# Carpetas a excluir por aparecer en la ruta (no indexar la propia app, basura del SO, etc.).
EXCLUDE_PATTERNS = [
    "MUSIC_BOX",
    ".venv",
    "node_modules",
    "__pycache__",
    "AppData",
    "$RECYCLE.BIN",
    "System Volume Information",
]


def index_db_path() -> Path:
    """Ruta única del índice SQLite que lee /api/music/library."""
    return settings.musicbox_root / "05_INDEXES" / "music_inventory.sqlite3"


def default_scan_roots() -> List[Path]:
    return [settings.music_master]


def is_excluded(path: Path) -> bool:
    path_str = str(path).replace("\\", "/")
    for pat in EXCLUDE_PATTERNS:
        if f"/{pat}/" in path_str or path_str.endswith(f"/{pat}"):
            return True
    return False


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_path TEXT UNIQUE,
            filename TEXT,
            extension TEXT,
            size_bytes INTEGER,
            root_source TEXT,
            artist TEXT,
            title TEXT,
            album TEXT,
            year TEXT,
            genre TEXT,
            duration_seconds REAL,
            bitrate INTEGER,
            indexed_at TEXT
        )
        """
    )
    c.execute("CREATE INDEX IF NOT EXISTS idx_artist ON tracks(artist)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_extension ON tracks(extension)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_root ON tracks(root_source)")
    conn.commit()
    return conn


def read_tags(path: Path) -> Dict[str, object]:
    try:
        audio = MutagenFile(str(path), easy=True)
        if not audio:
            return {}
        info = getattr(audio, "info", None)

        def first(*keys: str) -> str:
            for key in keys:
                value = audio.get(key)
                if value:
                    return str(value[0])[:500]
            return ""

        return {
            "artist": first("artist", "albumartist"),
            "title": first("title"),
            "album": first("album"),
            "year": first("date", "year"),
            "genre": first("genre"),
            "duration_seconds": float(getattr(info, "length", 0) or 0) if info else None,
            "bitrate": int(getattr(info, "bitrate", 0) or 0) if info else None,
        }
    except Exception:
        return {}


def build_index(
    roots: Optional[List[Path]] = None,
    db_path: Optional[Path] = None,
    max_errors: int = 200,
) -> Dict[str, object]:
    """Escanea las raíces, lee tags con mutagen y puebla el índice SQLite.

    No mueve ni borra archivos: solo lee. Es idempotente (INSERT OR REPLACE por ruta).
    """
    scan_roots = [Path(r) for r in (roots if roots is not None else default_scan_roots())]
    target_db = Path(db_path) if db_path is not None else index_db_path()

    conn = init_db(target_db)
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    total = 0
    bytes_total = 0
    by_ext: Dict[str, int] = {}
    errors: List[str] = []
    scanned_roots: List[str] = []
    skipped_roots: List[str] = []

    for root in scan_roots:
        if not root.exists():
            skipped_roots.append(str(root))
            continue
        scanned_roots.append(str(root))
        for path in root.rglob("*"):
            try:
                if not path.is_file() or is_excluded(path):
                    continue
                ext = path.suffix.lower()
                if ext not in AUDIO_EXTENSIONS:
                    continue
                size = path.stat().st_size
                tags = read_tags(path)
                cur.execute(
                    """
                    INSERT OR REPLACE INTO tracks
                    (full_path, filename, extension, size_bytes, root_source,
                     artist, title, album, year, genre, duration_seconds, bitrate, indexed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(path),
                        path.name,
                        ext,
                        size,
                        str(root),
                        tags.get("artist", ""),
                        tags.get("title", ""),
                        tags.get("album", ""),
                        tags.get("year", ""),
                        tags.get("genre", ""),
                        tags.get("duration_seconds"),
                        tags.get("bitrate"),
                        now,
                    ),
                )
                total += 1
                bytes_total += size
                by_ext[ext] = by_ext.get(ext, 0) + 1
                if total % 250 == 0:
                    conn.commit()
            except Exception as exc:  # noqa: BLE001 - se registra y se continúa
                if len(errors) < max_errors:
                    errors.append(f"{path}: {exc}")

    conn.commit()
    conn.close()

    return {
        "indexed": True,
        "db_path": str(target_db),
        "total": total,
        "bytes": bytes_total,
        "gb": round(bytes_total / (1024 ** 3), 2),
        "by_extension": dict(sorted(by_ext.items(), key=lambda kv: kv[1], reverse=True)),
        "scanned_roots": scanned_roots,
        "skipped_roots": skipped_roots,
        "error_count": len(errors),
        "errors": errors[:20],
    }
