from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query, Response

from app.services.indexer import build_index, query_inventory
from app.services.music_library import library_summary, list_audio_files, read_audio_tags

router = APIRouter(prefix="/api/music", tags=["music"])

MAX_FILES_LIMIT = 1000


@router.get("/summary")
def summary() -> dict:
    return library_summary()


@router.get(
    "/files",
    summary="Listar archivos de audio (paginado)",
    description=(
        "Escanea la biblioteca local y devuelve archivos de audio paginados. "
        f"`limit` admite hasta {MAX_FILES_LIMIT} por página; la respuesta incluye "
        "la cabecera `X-Total-Count` con el total de coincidencias."
    ),
)
def files(
    response: Response,
    limit: int = Query(100, ge=1, le=MAX_FILES_LIMIT, description=f"Elementos por página (máximo {MAX_FILES_LIMIT})."),
    offset: int = Query(0, ge=0, description="Desplazamiento inicial."),
    contains: str = Query("", description="Filtro de subcadena sobre la ruta del archivo."),
) -> dict:
    result = list_audio_files(limit=limit, offset=offset, contains=contains)
    response.headers["X-Total-Count"] = str(result.get("total", 0))
    return result


@router.get("/tags")
def tags(path: str) -> dict:
    return read_audio_tags(path)


@router.get(
    "/inventory",
    summary="Inventario unificado con duplicados",
    description=(
        "Devuelve el inventario indexado con marca de duplicados (por hash sha256 y por "
        "metadatos: mismo artista + álbum + título). Filtros: `source` (raíz de origen) y "
        "`status` (all / duplicated / unique). Paginado con cabecera `X-Total-Count`. "
        "Solo expone los duplicados; no borra nada."
    ),
)
def inventory(
    response: Response,
    limit: int = Query(100, ge=1, le=MAX_FILES_LIMIT, description=f"Elementos por página (máximo {MAX_FILES_LIMIT})."),
    offset: int = Query(0, ge=0, description="Desplazamiento inicial."),
    source: str = Query("", description="Filtrar por raíz de origen (root_source). Vacío = todas."),
    status: Literal["all", "duplicated", "unique"] = Query("all", description="Filtrar por estado de duplicado."),
) -> dict:
    result = query_inventory(limit=limit, offset=offset, source=source or None, status=status)
    response.headers["X-Total-Count"] = str(result.get("total", 0))
    return result


@router.post(
    "/reindex",
    summary="Reindexar la biblioteca",
    description=(
        "Escanea las raíces configuradas, lee tags con mutagen y reconstruye el "
        "índice SQLite que consume `/api/music/library`. Solo lee archivos; es una "
        "operación síncrona que puede tardar en bibliotecas grandes."
    ),
)
def reindex() -> dict:
    return build_index()
