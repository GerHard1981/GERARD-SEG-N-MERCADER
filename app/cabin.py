"""Cabin / MusicBox router.

Sirve la interfaz del reproductor (musicbox_cabin.html) y expone la
biblioteca de musica del disco local.

Las carpetas de musica se configuran con la variable de entorno MUSIC_DIRS
(rutas separadas por os.pathsep: ';' en Windows, ':' en Linux/Mac). En tu
portatil, por ejemplo:

    Windows PowerShell:
        $env:MUSIC_DIRS = "G:\\musica;G:\\MusicBox\\master;G:\\MusicBox\\biblioteca master;G:\\MusicBox\\duplicados;G:\\MusicBox\\musica no revision"

Si no se define, se usa la carpeta local app/music como ejemplo.
"""

from __future__ import annotations

import hashlib
import mimetypes
import os
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

AUDIO_EXTENSIONS = {
    ".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg",
    ".opus", ".wma", ".aiff", ".aif", ".alac",
}

HERE = Path(__file__).resolve().parent
HTML_FILE = HERE / "musicbox_cabin.html"


def get_music_dirs() -> list[Path]:
    """Carpetas de musica a escanear, desde MUSIC_DIRS o el default local."""
    raw = os.environ.get("MUSIC_DIRS", "").strip()
    if raw:
        dirs = [Path(p.strip()) for p in raw.split(os.pathsep) if p.strip()]
    else:
        dirs = [HERE / "music"]
    return [d for d in dirs if d.is_dir()]


def _track_id(path: Path) -> str:
    return hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:16]


def scan_library() -> dict[str, Path]:
    """Devuelve {id: ruta_absoluta} de todos los archivos de audio."""
    index: dict[str, Path] = {}
    for root in get_music_dirs():
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                ext = os.path.splitext(name)[1].lower()
                if ext in AUDIO_EXTENSIONS:
                    full = Path(dirpath) / name
                    index[_track_id(full)] = full
    return index


router = APIRouter()


@router.get("/cabin", response_class=HTMLResponse)
def cabin() -> HTMLResponse:
    if not HTML_FILE.is_file():
        raise HTTPException(status_code=404, detail="musicbox_cabin.html no encontrado")
    return HTMLResponse(HTML_FILE.read_text(encoding="utf-8"))


@router.get("/api/music/library")
def music_library() -> dict:
    index = scan_library()
    tracks = []
    for tid, path in sorted(index.items(), key=lambda kv: str(kv[1]).lower()):
        try:
            size = path.stat().st_size
        except OSError:
            size = None
        tracks.append({
            "id": tid,
            "title": path.stem,
            "filename": path.name,
            "ext": path.suffix.lower().lstrip("."),
            "size": size,
        })
    return {
        "count": len(tracks),
        "directories": [str(d) for d in get_music_dirs()],
        "tracks": tracks,
    }


@router.get("/api/music/stream/{track_id}")
def music_stream(track_id: str) -> FileResponse:
    index = scan_library()
    path = index.get(track_id)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Pista no encontrada")
    media_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    # FileResponse de Starlette soporta peticiones Range (seek en el navegador).
    return FileResponse(path, media_type=media_type, filename=path.name)


app = FastAPI(title="GSM Cabin / MusicBox")
app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765)
