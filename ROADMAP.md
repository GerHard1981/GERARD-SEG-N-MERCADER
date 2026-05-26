# ROADMAP — MusicBox Discogs API

## Estado actual

API FastAPI funcionando en `127.0.0.1:8765`, cliente Discogs con caché SQLite,
matching local y Cabin básica.

## Fase 1 (en curso)

- Tests automatizados.
- Manejo de errores.
- Mejora de indexado.
- Paginación consistente.
- Cabin mobile-first.

## Próximos pasos inmediatos

1. Tests automatizados (pytest + httpx).
2. Excepciones tipadas en `discogs_client.py` con códigos HTTP correctos.
3. Revisar consistencia de paginación: `/api/music/files` y `/api/music/library`
   ya aceptan `limit`/`offset`; pendiente añadir cabeceras `X-Total-Count` y
   documentar límites máximos en Swagger.
4. Ampliar `/health` con estado de Discogs, tamaño de caché y matches guardados.
5. Refactorizar `app/cabin.py` separando HTML a `app/static/index.html`.
