from __future__ import annotations

import hashlib
import re
import sqlite3
from collections import Counter
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

# Columnas del inventario que se devuelven en lecturas (sin recalcular nada pesado).
_INVENTORY_COLUMNS = (
    "id, full_path, filename, extension, size_bytes, root_source, "
    "artist, album, title, year, genre, sha256, indexed_at"
)


def index_db_path() -> Path:
    """Ruta única del índice SQLite que lee /api/music/library y /api/music/inventory."""
    return settings.musicbox_root / "05_INDEXES" / "music_inventory.sqlite3"


def default_scan_roots() -> List[Path]:
    """Raíces a escanear: multi-ruta vía MUSIC_ROOTS, con fallback a music_master."""
    return list(settings.music_roots)


def is_excluded(path: Path) -> bool:
    path_str = str(path).replace("\\", "/")
    for pat in EXCLUDE_PATTERNS:
        if f"/{pat}/" in path_str or path_str.endswith(f"/{pat}"):
            return True
    return False


def _norm(value: object) -> str:
    """Normaliza texto para comparar metadatos (minúsculas, sin signos)."""
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Hash sha256 del contenido del archivo (lectura por bloques). '' si falla."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    # Acelera las inserciones masivas sin cambiar los datos resultantes.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
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
            sha256 TEXT,
            indexed_at TEXT
        )
        """
    )
    # Migración para índices creados antes de añadir la columna sha256.
    cols = {row[1] for row in c.execute("PRAGMA table_info(tracks)")}
    if "sha256" not in cols:
        c.execute("ALTER TABLE tracks ADD COLUMN sha256 TEXT")
    c.execute("CREATE INDEX IF NOT EXISTS idx_artist ON tracks(artist)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_extension ON tracks(extension)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_root ON tracks(root_source)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sha256 ON tracks(sha256)")
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
    """Escanea las raíces, lee tags con mutagen, calcula sha256 y puebla el índice SQLite.

    No mueve ni borra archivos: solo lee. Es idempotente (INSERT OR REPLACE por ruta).
    Cada track guarda su ruta, hash sha256, tags, fecha de indexado y raíz de origen.
    """
    scan_roots = [Path(r) for r in (roots if roots is not None else default_scan_roots())]
    target_db = Path(db_path) if db_path is not None else index_db_path()

    conn = init_db(target_db)
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    total = 0
    bytes_total = 0
    by_ext: Dict[str, int] = {}
    by_root: Dict[str, int] = {}
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
                     artist, title, album, year, genre, duration_seconds, bitrate, sha256, indexed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        file_sha256(path),
                        now,
                    ),
                )
                total += 1
                bytes_total += size
                by_ext[ext] = by_ext.get(ext, 0) + 1
                by_root[str(root)] = by_root.get(str(root), 0) + 1
                if total % 250 == 0:
                    conn.commit()
            except Exception as exc:  # noqa: BLE001 - se registra y se continú
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
        "by_root": by_root,
        "scanned_roots": scanned_roots,
        "skipped_roots": skipped_roots,
        "error_count": len(errors),
        "errors": errors[:20],
    }


def _meta_key(row: sqlite3.Row) -> tuple:
    return (_norm(row["artist"]), _norm(row["album"]), _norm(row["title"]))


def _has_meta(row: sqlite3.Row) -> bool:
    # Solo consideramos duplicado por metadatos si hay algo identificable.
    return bool(_norm(row["artist"]) or _norm(row["title"]))


def query_inventory(
    db_path: Optional[Path] = None,
    limit: int = 100,
    offset: int = 0,
    source: Optional[str] = None,
    status: str = "all",
) -> Dict[str, object]:
    """Inventario unificado con marca de duplicados (por hash y por metadatos).

    Filtros: `source` (raíz de origen) y `status` (all | duplicated | unique).
    No borra nada: solo expone. Devuelve también `total` para paginar con X-Total-Count.
    """
    target_db = Path(db_path) if db_path is not None else index_db_path()
    if not target_db.exists():
        return {"indexed": False, "total": 0, "returned": 0, "limit": limit, "offset": offset,
                "source": source, "status": status, "items": []}

    with sqlite3.connect(target_db) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            f"SELECT {_INVENTORY_COLUMNS} FROM tracks ORDER BY artist, album, title, full_path"
        ).fetchall()

    hash_counts = Counter(r["sha256"] for r in rows if r["sha256"])
    meta_counts = Counter(_meta_key(r) for r in rows if _has_meta(r))

    items: List[Dict[str, object]] = []
    sources_seen = set()
    for r in rows:
        sources_seen.add(r["root_source"])
        dup_hash = bool(r["sha256"]) and hash_counts[r["sha256"]] > 1
        dup_meta = _has_meta(r) and meta_counts[_meta_key(r)] > 1
        is_dup = bool(dup_hash or dup_meta)

        if source and r["root_source"] != source:
            continue
        if status == "duplicated" and not is_dup:
            continue
        if status == "unique" and is_dup:
            continue

        items.append({
            "id": r["id"],
            "path": r["full_path"],
            "filename": r["filename"],
            "extension": r["extension"],
            "size_bytes": r["size_bytes"],
            "root_source": r["root_source"],
            "artist": r["artist"] or "",
            "album": r["album"] or "",
            "title": r["title"] or r["filename"] or "",
            "year": r["year"] or "",
            "sha256": r["sha256"] or "",
            "indexed_at": r["indexed_at"],
            "duplicate": is_dup,
            "duplicate_by_hash": bool(dup_hash),
            "duplicate_by_metadata": bool(dup_meta),
        })

    total = len(items)
    page = items[offset:offset + limit]
    return {
        "indexed": True,
        "total": total,
        "returned": len(page),
        "limit": limit,
        "offset": offset,
        "source": source,
        "status": status,
        "sources": sorted(s for s in sources_seen if s),
        "items": page,
    }
