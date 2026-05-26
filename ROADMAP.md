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

## Fase 2 — completado

- [x] **1. Tests automatizados (pytest + httpx).** Suite en `tests/`
  (`test_api.py`, `test_discogs_exceptions.py`) con `pytest.ini` y
  `requirements-dev.txt`.
- [x] **2. Excepciones tipadas en `discogs_client.py`.** Jerarquía
  `DiscogsError` → `DiscogsAuthError` (401), `DiscogsForbiddenError` (403),
  `DiscogsNotFoundError` (404), `DiscogsRateLimitError` (429),
  `DiscogsNetworkError` (503); helper `exception_for_status` y handler en
  `app/main.py` que devuelve el código HTTP correcto.
- [x] **3. Paginación consistente.** `/api/music/files` y `/api/music/library`
  emiten la cabecera `X-Total-Count`; límites máximos documentados en Swagger
  (`limit` ≤ 1000 en `/files`, ≤ 5000 en `/library`) y expuestos vía CORS.
- [x] **4. `/health` ampliado** con estado de Discogs (token, base, user-agent),
  tamaño y TTL de la caché SQLite, y número de matches guardados.
- [x] **5. Refactor de `app/cabin.py`** con el HTML separado a
  `app/static/index.html` (entregado en la Fase 1 / PR #1).

## Pendiente / siguiente

- Mejora de indexado (`index_music.py`) y verificación de matches de Discogs
  (hoy se guardan como `top_result_unverified`).
- App de escritorio (Electron) replicando las pantallas de la web.
