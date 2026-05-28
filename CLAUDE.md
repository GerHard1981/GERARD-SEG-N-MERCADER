# CLAUDE.md — MusicBox Discogs API

## Resumen del proyecto

MusicBox Discogs API es una API REST local desarrollada con FastAPI que actúa como puente entre la biblioteca de música local del usuario y la base de datos de Discogs. Permite buscar lanzamientos, artistas, labels y masters en Discogs, leer los metadatos de archivos de audio locales y hacer matching automático entre archivos locales y entradas de Discogs. La API corre en local en el puerto 8765 y expone una interfaz Swagger en http://127.0.0.1:8765/docs.

Además de la API, el proyecto sirve una **interfaz web mobile-first** en la ruta raíz `/` (Biblioteca con búsqueda en vivo y paginación, Reproductor y Detalle de track con datos de Discogs), incluye un **indexador real** de la biblioteca, **tests automatizados** (pytest) e **integración continua** (GitHub Actions). Los resultados de matching se persisten en SQLite local y nunca se modifican archivos de audio ni se mueven ficheros.

## Stack técnico

- fastapi 0.115.0 — Framework web principal, define los endpoints
- uvicorn 0.30.0 — Servidor ASGI que ejecuta la aplicación
- requests 2.32.0 — Llamadas HTTP a la API de Discogs
- mutagen 1.47.0 — Lectura de metadatos (tags) de archivos audio
- pydantic 2.8.0 — Validación y serialización de modelos de datos
- python-dotenv 1.0.1 — Carga de variables de entorno desde .env
- pytest + httpx — Tests automatizados (en `requirements-dev.txt`)

La interfaz web es HTML/CSS/JS sin dependencias (vanilla) en `app/static/index.html`.

## Estructura de carpetas y archivos principales

```
musicbox_discogs_api/
├── app/
│   ├── main.py — Punto de entrada FastAPI, registra routers, middleware CORS y handler de excepciones Discogs
│   ├── cabin.py — Sirve la web en / (app/static/index.html), librería indexada (SQLite) y streaming de audio
│   ├── static/
│   │   └── index.html — Interfaz web mobile-first/tablet: Biblioteca, Reproductor, Detalle
│   ├── core/config.py — Settings (dataclass): rutas, credenciales Discogs, puerto API
│   ├── connectors/discogs_client.py — Cliente HTTP de Discogs con caché SQLite y excepciones tipadas
│   ├── routers/
│   │   ├── health.py — GET /health — estado de la app, Discogs, caché y matches
│   │   ├── music.py — GET /api/music/summary, /files, /tags y POST /api/music/reindex
│   │   └── discogs.py — GET/POST /api/discogs/* — búsquedas, releases, matching, matches guardados
│   └── services/
│       ├── matcher.py — Matching archivo/carpeta → Discogs + scoring de confianza
│       ├── music_library.py — Lectura de la biblioteca de música local
│       └── indexer.py — Indexador: escanea audio, lee tags y puebla music_inventory.sqlite3
├── index_music.py — CLI del indexador
├── tests/ — Suite de tests (pytest)
├── data/ — (generado en runtime) SQLite: caché Discogs y matches
├── ROADMAP.md — Estado y próximos pasos del proyecto
├── pytest.ini — Configuración de pytest
├── requirements.txt — Dependencias Python (runtime)
├── requirements-dev.txt — Dependencias de desarrollo (pytest, httpx)
├── .github/workflows/
│   ├── ci.yml — CI: py_compile + pytest en cada push a main y cada PR
│   ├── claude.yml — Integración de Claude Code (@claude en issues/PRs)
│   └── claude-code-review.yml — Revisión automática de PRs con Claude
├── .env — Variables de entorno locales (NO versionar)
├── .env.example — Plantilla de variables de entorno
├── run_api.ps1 — Script principal para arrancar el servidor en local
├── _start_musicbox_api_server.ps1 — Wrapper con cabecera de bienvenida
├── check_discogs.ps1 — Script de diagnóstico de conexión con Discogs
├── edit_env.ps1 — Abre .env en el editor para configurar credenciales
└── open_docs.ps1 — Abre http://127.0.0.1:8765/docs en el navegador
```

## Cómo arrancar la API en local

Opción A (doble clic o PowerShell):
```
cd "G:\Mi unidad\MUSIC_BOX\APP\musicbox_discogs_api"
.\_start_musicbox_api_server.ps1
```

Opción B (arranque directo):
```
cd "G:\Mi unidad\MUSIC_BOX\APP\musicbox_discogs_api"
.\run_api.ps1
```

Una vez arrancada, la interfaz web está en http://127.0.0.1:8765/ y Swagger en http://127.0.0.1:8765/docs.

## Cómo configurar las credenciales de Discogs

1. Crear el token en Discogs: Settings → Developers → Generate new token. No compartas el token.
2. Copiar plantilla: `Copy-Item .env.example .env` (o usar `.\edit_env.ps1`).
3. Variables esperadas en .env:
   ```
   MUSIC_MASTER=C:\Users\<tu_usuario>\Google Drive\Music_Master
   MUSICBOX_ROOT=C:\Users\<tu_usuario>\Google Drive\MUSIC_BOX
   DISCOGS_TOKEN=<pega aquí tu token>
   DISCOGS_USER_AGENT=MusicBoxDiscogs/0.1 +local
   DISCOGS_API_BASE=https://api.discogs.com
   DISCOGS_CACHE_TTL_SECONDS=604800
   MUSICBOX_API_HOST=127.0.0.1
   MUSICBOX_API_PORT=8765
   ```
4. Verificar conexión: `.\check_discogs.ps1` o GET http://127.0.0.1:8765/api/discogs/config.

## Convenciones del proyecto

- Ruta del código fuente en local: G:\Mi unidad\MUSIC_BOX\APP\musicbox_discogs_api
- La música pesada (archivos de audio, colecciones) NUNCA va dentro de MUSIC_BOX. Los archivos de audio residen en Music_Master (Google Drive) o equivalentes. MUSIC_BOX contiene únicamente la aplicación, índices y configuración.
- Idioma de toda comunicación: castellano (español de Catalunya). Ni catalán, ni inglés salvo en nombres de variables, funciones y rutas de código.
- La API es de solo lectura: no borra música, no mueve ficheros, no sobrescribe tags de audio.
- Los matches se guardan en data/musicbox_discogs_matches.sqlite3.
- La caché de Discogs se guarda en data/discogs_cache.sqlite3 (TTL por defecto: 7 días).
- No versionar el archivo .env (ya está en .gitignore).
- Cuenta de Google Drive asociada: segunmercader.g@gmail.com

## Endpoints principales

- GET / — Interfaz web mobile-first (Biblioteca, Reproductor, Detalle), servida desde app/static/index.html
- GET /health — Estado de la app, configuración de Discogs, tamaño/TTL de la caché y número de matches
- GET /api/music/summary — Resumen de la biblioteca local
- GET /api/music/files — Lista paginada de archivos de audio locales (cabecera `X-Total-Count`, `limit` ≤ 1000)
- GET /api/music/tags — Tags de un archivo de audio concreto
- GET /api/music/library — Librería indexada (SQLite), búsqueda + paginación (cabecera `X-Total-Count`, `limit` ≤ 5000)
- GET /api/music/stream — Streaming de audio (soporta Range)
- POST /api/music/reindex — Reconstruye el índice SQLite de la biblioteca
- GET /api/discogs/config — Estado de la configuración de Discogs
- GET /api/discogs/me — Identidad del usuario en Discogs
- GET /api/discogs/search — Búsqueda en Discogs (release/master/...)
- GET /api/discogs/releases/{release_id}, /masters/{master_id}, /artists/{artist_id}, /labels/{label_id}
- POST /api/discogs/match-file — Matching de un archivo local (guarda score de confianza)
- POST /api/discogs/match-folder — Matching de una carpeta completa
- GET /api/discogs/matches — Matches guardados (por `path` o los más recientes)
- POST /api/discogs/matches/{id}/verify — Marca un match como verificado

Los endpoints de recurso de Discogs propagan el estado de la API de Discogs como códigos HTTP correctos mediante excepciones tipadas (401/403/404/429/503).

## Comandos útiles de desarrollo

- Arrancar: `.\run_api.ps1`
- Instalar deps (runtime): `python -m pip install -r requirements.txt`
- Instalar deps de desarrollo: `python -m pip install -r requirements-dev.txt`
- Ejecutar tests: `python -m pytest -q`
- Indexar la biblioteca (CLI): `python index_music.py`
- Abrir Swagger: `.\open_docs.ps1`
- Editar credenciales: `.\edit_env.ps1`
- Verificar Discogs: `.\check_discogs.ps1`
- Uvicorn directo: `$env:PYTHONPATH = (Get-Location).Path; python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload`
- Health: `Invoke-RestMethod http://127.0.0.1:8765/health`

## Estado del desarrollo (PRs mergeados)

- **#1 — Web mobile-first**: refactor de la capa web; HTML separado a `app/static/index.html`, ruta `/cabin` renombrada a `/`, pantallas Biblioteca / Reproductor / Detalle (vertical y horizontal).
- **#2 — Fase 2 del roadmap**: tests automatizados (pytest), excepciones tipadas en `discogs_client.py` con códigos HTTP correctos, paginación consistente con cabecera `X-Total-Count`, y `/health` enriquecido (Discogs, caché, matches).
- **#3 — Indexador**: servicio de indexado real (`app/services/indexer.py`), CLI `index_music.py`, endpoint `POST /api/music/reindex` y botón "Indexar biblioteca" en la web.
- **#4 — Verificación de Discogs**: scoring de confianza de los matches, lectura de matches guardados (`GET /api/discogs/matches`) y verificación manual (`POST /api/discogs/matches/{id}/verify`).
- **#5 — CI**: workflow de GitHub Actions (`py_compile` + `pytest`) en cada push a `main` y cada PR.
