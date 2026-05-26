from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

from mutagen import File as MutagenFile

from app.core.config import settings

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".aiff", ".aif", ".m4a", ".ogg"}


def iter_audio_files(root: Optional[Path] = None) -> Iterable[Path]:
    base = root or settings.music_master
    if not base.exists():
        return []
    for path in base.rglob("*"):
        try:
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
                yield path
        except OSError:
            continue


def library_summary() -> Dict[str, object]:
    total = 0
    bytes_total = 0
    by_ext: Dict[str, int] = {}
    top_folders: Dict[str, int] = {}

    for path in iter_audio_files():
        total += 1
        try:
            bytes_total += path.stat().st_size
        except OSError:
            pass
        ext = path.suffix.lower()
        by_ext[ext] = by_ext.get(ext, 0) + 1
        folder = str(path.parent)
        top_folders[folder] = top_folders.get(folder, 0) + 1

    top = sorted(top_folders.items(), key=lambda kv: kv[1], reverse=True)[:50]
    return {
        "music_master": str(settings.music_master),
        "exists": settings.music_master.exists(),
        "total_audio": total,
        "gb": round(bytes_total / (1024 ** 3), 2),
        "by_extension": dict(sorted(by_ext.items(), key=lambda kv: kv[1], reverse=True)),
        "top_folders": [{"folder": folder, "count": count} for folder, count in top],
    }


def list_audio_files(limit: int = 100, offset: int = 0, contains: str = "") -> Dict[str, object]:
    rows: List[Dict[str, object]] = []
    contains_l = contains.lower().strip()
    skipped = 0
    scanned = 0
    for path in iter_audio_files():
        scanned += 1
        if contains_l and contains_l not in str(path).lower():
            continue
        if skipped < offset:
            skipped += 1
            continue
        if len(rows) >= limit:
            break
        stat = None
        try:
            stat = path.stat()
        except OSError:
            pass
        rows.append(
            {
                "path": str(path),
                "name": path.name,
                "folder": str(path.parent),
                "extension": path.suffix.lower(),
                "bytes": stat.st_size if stat else None,
                "modified": stat.st_mtime if stat else None,
            }
        )
    return {"limit": limit, "offset": offset, "returned": len(rows), "scanned": scanned, "files": rows}


def read_audio_tags(path: str) -> Dict[str, object]:
    p = Path(path)
    result: Dict[str, object] = {
        "path": str(p),
        "exists": p.exists(),
        "extension": p.suffix.lower(),
        "artist": None,
        "album": None,
        "title": None,
        "tracknumber": None,
        "date": None,
        "raw_keys": [],
    }
    if not p.exists() or not p.is_file():
        return result

    try:
        audio = MutagenFile(str(p), easy=True)
    except Exception as exc:
        result["error"] = str(exc)
        audio = None

    if audio and audio.tags:
        result["raw_keys"] = sorted(list(audio.tags.keys()))
        def first(*keys: str):
            for key in keys:
                value = audio.tags.get(key)
                if isinstance(value, list) and value:
                    return value[0]
                if isinstance(value, str):
                    return value
            return None
        result["artist"] = first("artist", "albumartist", "composer")
        result["album"] = first("album")
        result["title"] = first("title")
        result["tracknumber"] = first("tracknumber")
        result["date"] = first("date", "year")

    # Fallback: parse file stem with common separators.
    if not result["title"]:
        stem = p.stem.replace("_", " ").strip()
        if " - " in stem:
            artist, title = stem.split(" - ", 1)
            result["artist"] = result["artist"] or artist.strip()
            result["title"] = title.strip()
        else:
            result["title"] = stem
    return result
