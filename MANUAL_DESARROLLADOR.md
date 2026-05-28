# MANUAL DEL DESARROLLADOR — MusicBox Discogs API

> Documento técnico de referencia para el creador/desarrollador del proyecto.
> Recoge la visión, la arquitectura, el historial de cambios y las decisiones técnicas.
> Última actualización: mayo 2026.

---

## 1. Introducción y visión

**MusicBox Discogs API** es una API REST local (FastAPI) que, junto a una interfaz web mobile-first, aspira a convertirse en la **herramienta central de trabajo de un DJ profesional**: un sistema que unifique toda su música, independientemente de dónde esté almacenada o qué software utilice, y que le permita gestionar, enriquecer, comprar y tocar sin saltar entre aplicaciones fragmentadas.

La meta a largo plazo es indexar bibliotecas dispersas (disco local, pendrives, NAS, Google Drive), normalizar los formatos hacia un estándar único (WAV sin pérdidas), enriquecer metadatos cruzando con Discogs, e integrarse progresivamente con plataformas de compra/streaming (Beatport, Tidal, SoundCloud), softwares DJ (Rekordbox, Serato, Traktor, Engine DJ) y hardware físico (Pioneer DJ, Rane, Native Instruments, Numark, Reloop, Technics).

El detalle completo de fases vive en `ROADMAP.md`. El contexto operativo para asistentes de IA vive en `CLAUDE.md`. Este manual documenta **cómo se ha construido** y **por qué**.

---

## 2. Stack tecnológico

| Componente | Tecnología | Uso |
|---|---|---|
| Framework web | FastAPI 0.115.0 | Define los endpoints REST |
| Servidor ASGI | Uvicorn 0.30.0 | Ejecuta la aplicación |
| HTTP cliente | requests 2.32.0 | Llamadas a la API de Discogs |
| Metadatos audio | mutagen 1.47.0 | Lectura de tags de archivos |
| Validación | pydantic 2.8.0 | Modelos de datos |
| Configuración | python-dotenv 1.0.1 | Variables de entorno (.env) |
| Tests | pytest + httpx | Suite automatizada (requirements-dev.txt) |
| Persistencia | SQLite | Caché Discogs, matches, índice |
| Frontend | HTML/CSS/JS vanilla | Sin frameworks ni dependencias |
| CI | GitHub Actions | py_compile + pytest en cada push/PR |

**Principio clave:** el proyecto es 100% Python en el backend y vanilla en el frontend. No hay Node, ni Electron, ni frameworks JS. Esto se decidió para mantener la base ligera, sin trial-and-error y con un único entorno de ejecución.

---

## 3. Arquitectura del proyecto

```
musicbox_discogs_api/
├── app/
│   ├── main.py              # Entrada FastAPI: routers, CORS, handler de excepciones Discogs
│   ├── cabin.py             # Sirve la web en / , librería indexada y streaming de audio
│   ├── static/
│   │   └── index.html       # Interfaz web mobile-first: 10 secciones + cabina DJ
│   ├── core/
│   │   └── config.py        # Settings centralizados (rutas, credenciales, puerto)
│   ├── connectors/
│   │   └── discogs_client.py# Cliente Discogs con caché SQLite y excepciones tipadas
│   ├── routers/
│   │   ├── health.py        # GET /health enriquecido
│   │   ├── music.py         # /api/music/* (files, library, tags, reindex, summary)
│   │   └── discogs.py       # /api/discogs/* (search, releases, match, matches, verify)
│   └── services/
│       ├── matcher.py       # Matching archivo/carpeta → Discogs + scoring de confianza
│       ├── music_library.py # Lectura de la biblioteca local
│       └── indexer.py       # Indexador: escanea audio y puebla music_inventory.sqlite3
├── index_music.py           # CLI del indexador
├── tests/                   # Suite pytest
├── data/                    # (runtime, ignorado por git) SQLite: caché y matches
├── ROADMAP.md               # Plan por fases
├── CLAUDE.md                # Contexto operativo para asistentes de IA
├── pytest.ini
├── requirements.txt         # Dependencias runtime
├── requirements-dev.txt     # Dependencias de test
├── .github/workflows/
│   └── ci.yml               # CI: py_compile + pytest
├── .env / .env.example
└── *.ps1                    # Scripts de arranque y utilidades (Windows)
```

### Principios de diseño del código

- **Servicios independientes:** cada módulo de `app/services/` es testable de forma aislada y no acopla con FastAPI.
- **Routers sin lógica de negocio:** los routers consumen servicios; la lógica vive en los servicios.
- **Connectors aíslan lo externo:** `discogs_client.py` encapsula toda la integración con Discogs y expone excepciones tipadas. Cuando se añadan más plataformas, cada una tendrá su connector.
- **Convención de API:** rutas en kebab-case bajo `/api/{recurso}`; paginación con `limit`/`offset` y cabecera `X-Total-Count` expuesta vía CORS; errores con códigos HTTP correctos (nunca 200 con `error` en el cuerpo).

---

## 4. Estructura de la interfaz web (10 secciones)

La web tiene una barra lateral (drawer con hamburguesa en móvil, sidebar fija en tablet horizontal). Mobile-first; no optimizada para PC.

| # | Sección | Estado | Descripción |
|---|---|---|---|
| 1 | Biblioteca musical | **Funcional** | Búsqueda en vivo, paginación, reproductor, detalle con datos de Discogs |
| 2 | Convertidor a WAV | Próximamente | Conversión a WAV sin pérdidas con ffmpeg |
| 3 | Organizador | Próximamente | Renombrar, ordenar y exportar a USB/pendrives/controladores DJ |
| 4 | DJ | **Cabina visual** | Cabina estilo Rane Performer: 2 decks, mixer 4 canales, 8 pads, FX, pantalla completa (sin audio aún) |
| 5 | Discogs | **Funcional** | Buscador, matches guardados con score/estado, verificación |
| 6 | Aplicaciones | Próximamente | Integración con YouTube, YouTube Music, SoundCloud, Tidal, Beatport, Beatsource, Juno |
| 7 | Blog | Próximamente | Novedades, tutoriales y notas técnicas |
| 8 | Soporte técnico | Próximamente | Guías de instalación, configuración y resolución de problemas |
| 9 | Tienda música digital | Próximamente | Compra de música (sujeto a partnerships) |
| 10 | Producción musical | Próximamente | Crear música desde cero dentro de MusicBox |

---

## 5. Historial de desarrollo (Pull Requests)

Todo el desarrollo se ha hecho mediante PRs revisados antes de mergear a `main`.

### PR #1 — Web mobile-first
Refactor de la capa web. Se separó el HTML (antes incrustado en `cabin.py`) a `app/static/index.html`. Se renombró la ruta `/cabin` a `/` (raíz). Se crearon las pantallas Biblioteca, Reproductor y Detalle, diseñadas para vertical (móvil) y horizontal (tablet).

### PR #2 — Fase 2 del roadmap
- Tests automatizados con pytest + httpx.
- Excepciones tipadas en `discogs_client.py` (`DiscogsAuthError` 401, `DiscogsForbiddenError` 403, `DiscogsNotFoundError` 404, `DiscogsRateLimitError` 429, `DiscogsNetworkError` 503), con handler en `main.py` que las traduce a códigos HTTP correctos.
- Paginación consistente con cabecera `X-Total-Count` expuesta vía CORS, y límites documentados en Swagger (1000 en `/files`, 5000 en `/library`).
- `/health` enriquecido: estado de Discogs, tamaño/TTL de la caché y número de matches guardados, con degradación segura si las bases de datos no existen.

### PR #3 — Indexador
- Servicio de indexado real (`app/services/indexer.py`) que escanea audio, lee tags y puebla `music_inventory.sqlite3`.
- CLI `index_music.py` para indexar desde terminal.
- Endpoint `POST /api/music/reindex` para indexar desde la web.
- Botón "Indexar biblioteca" en la interfaz.

### PR #4 — Verificación de Discogs
- Scoring de confianza de los matches.
- Lectura de matches guardados: `GET /api/discogs/matches`.
- Verificación manual: `POST /api/discogs/matches/{id}/verify`.

### PR #5 — Integración continua (CI)
Workflow de GitHub Actions (`.github/workflows/ci.yml`) que ejecuta `py_compile` + `pytest` en cada push a `main` y en cada PR. Red de seguridad permanente: cualquier PR que rompa los tests se detecta automáticamente.

### PR #7 — Visión completa + Cabina DJ
- Barra lateral con las 10 secciones del producto (drawer en móvil, sidebar en tablet).
- Secciones funcionales conectadas a su contenido real (Biblioteca, Discogs).
- Resto de secciones como placeholders elegantes con descripción.
- Cabina DJ a pantalla completa (estilo Rane Performer): 2 decks con jog wheel/EQ/pitch, mixer de 4 canales con knobs/faders/crossfader, 8 performance pads que se iluminan, sección FX (DRY/WET, TIME, FEEDBACK), botón de pantalla completa (Fullscreen API). Controles visuales, todavía sin audio.

### PR #8 — Documentación (CLAUDE.md)
Se añadió `CLAUDE.md` a la raíz como documento de contexto operativo para asistentes de IA.

### PR #6 — Cerrado (no mergeado)
PR de optimización del indexador. Se cerró porque tocaba el `index.html` antiguo de 3 pantallas y entraba en conflicto con la web de 10 secciones ya en `main`. La parte útil (PRAGMA WAL del indexador) está anotada para reintroducirse en un PR limpio.

---

## 6. Decisiones técnicas clave

- **Python puro, sin Node/Electron.** Una sola tecnología, un solo entorno, menos puntos de fallo. La web es vanilla por el mismo motivo.
- **Mobile-first y tablet, no PC.** El DJ trabaja con móvil/tablet en cabina; la web se diseña para esos formatos primero.
- **API de solo lectura.** No borra música, no mueve ficheros, no sobrescribe tags. La seguridad de la biblioteca del usuario es prioritaria.
- **Música pesada fuera de la app.** Los archivos de audio residen en `Music_Master` (Google Drive) o equivalentes. La carpeta `MUSIC_BOX` contiene únicamente la aplicación, índices y configuración.
- **Idioma:** toda la comunicación y la UI en castellano (español de Catalunya). El código (variables, funciones) en inglés.
- **Honestidad técnica:** las integraciones que requieren partnership comercial (Beatport, Tidal) están marcadas como condicionadas y no se prometen como features independientes. No se implementa descifrado de DRM.

---

## 7. Flujo de trabajo de desarrollo

1. El desarrollo de código lo ejecuta **Claude Code** sobre el repo de GitHub.
2. Cada tarea se hace en una **rama nueva** con prefijo (`feat/`, `fix/`, `docs/`, `refactor/`).
3. Se abre un **PR en estado draft** contra `main`.
4. El PR se revisa (contenido, tests, conflictos) antes de pasarlo a "Ready for review".
5. **Squash & merge** y borrado de la rama.
6. Cada PR cierra **un único objetivo**.

**Reglas de calidad innegociables:**
- Cada PR trae tests si añade servicios o endpoints.
- `pytest` debe estar en verde antes de mergear.
- `py_compile` de todo `app/`, `tests/` e `index_music.py` sin errores.
- Sin dependencias nuevas salvo que sean imprescindibles y justificadas.

---

## 8. Infraestructura y repositorios

- **Repo principal:** `GerHard1981/musicboxdiscogsapi` (GitHub). Fuente de verdad.
- **Repo legacy archivado:** `GerHard1981/musicboxdiscogsapilegacy` (read-only). Conserva la historia previa.
- **Código local:** `G:\Mi unidad\MUSIC_BOX\APP\musicbox_discogs_api` (Google Drive). Para arrancar y probar en local.
- **Cuenta de Drive asociada:** segunmercader.g@gmail.com
- **CI:** GitHub Actions ejecuta los tests en cada push/PR.

---

## 9. Problemas resueltos y lecciones aprendidas

Documentado para no repetir errores:

- **Doble repositorio.** Existían dos repos con el mismo proyecto en distinto estado (`GERARD-SEG-N-MERCADER` con el trabajo nuevo y `musicbox-discogs-api` original). Se consolidó renombrando: el repo del trabajo nuevo pasó a `musicboxdiscogsapi` y el viejo a `musicboxdiscogsapilegacy` (archivado).
- **Push bloqueado tras el rename.** Tras renombrar el repo en GitHub, el proxy de la sesión de Claude Code mantenía la allowlist con el nombre antiguo: las lecturas redirigían pero las escrituras (`git-receive-pack`) devolvían 503/502. Solución práctica: subir los archivos generados manualmente vía la interfaz web de GitHub.
- **`.venv` en Google Drive.** Un entorno virtual creado dentro de Drive deja archivos "solo en la nube"; al arrancar, `Activate.ps1` no se encuentra. Solución: trabajar con el código fuera de Drive (carpeta local) o marcar el `.venv` como "Disponible sin conexión".
- **Cabina DJ eliminada por error.** En el primer refactor se instruyó retirar la "Cabin DJ" para sustituirla por una interfaz general. Se recuperó después como sección DJ dedicada (PR #7).

---

## 10. Estado actual

- `main` contiene: web mobile-first con 10 secciones, cabina DJ, indexador, verificación de Discogs, tests, CI y documentación (CLAUDE.md, ROADMAP.md).
- La API arranca en local en `http://127.0.0.1:8765`. La web en `/`, Swagger en `/docs`.
- Tests: 24 en verde.

---

## 11. Roadmap inmediato / pendientes

- Reintroducir la optimización del indexador (`PRAGMA journal_mode=WAL` + `synchronous=NORMAL`) en un PR limpio.
- Subir los 2 workflows de Claude (`claude.yml`, `claude-code-review.yml`) una vez configurado el secreto `CLAUDE_CODE_OAUTH_TOKEN` en GitHub.
- Fase 2 del roadmap: indexador multi-ruta, hash de archivos, deduplicación, conversión a WAV con ffmpeg.
- Dotar de audio real a la cabina DJ.

---

## 12. Notas para los próximos manuales

Documentación a preparar más adelante (material a ir guardando desde ahora):

### Manual de instalación (pendiente)
Debe cubrir: requisitos previos (Python, Git), descarga del repo, creación del `.venv`, instalación de dependencias, configuración del `.env` (token de Discogs, rutas de música), y arranque con los scripts `.ps1`. Incluir resolución de los problemas conocidos (apartado 9).

### Manual de usuario (pendiente)
Debe cubrir: cómo abrir la web, recorrido por las 10 secciones, cómo indexar la biblioteca, cómo buscar y reproducir música, cómo usar la sección Discogs (búsqueda, matches, verificación), y cómo usar la cabina DJ. Orientado a usuario no técnico, con capturas.
