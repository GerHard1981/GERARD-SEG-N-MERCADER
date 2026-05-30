# AGENTS.md — Directrices para agentes de código (Codex, Claude Code y otros)

> Este archivo lo leen los agentes automáticos (Codex CLI, etc.).
> **Fuente de verdad del proyecto:** `CLAUDE.md`. **Cómo se trabaja:** `WORKFLOW.md`.
> Aquí van solo las **reglas innegociables**, resumidas, para cualquier agente.

## Reparto de roles

- **Claude Code** es el agente principal (planifica, implementa, abre PRs). Tiene dos
  subagentes de proyecto en `.claude/agents/`: **`musicbox-dev`** (implementa) y
  **`musicbox-reviewer`** (revisa diffs; solo lectura).
- **Codex** actúa como segunda opinión / revisor. Lee este `AGENTS.md` como directrices.
- **Regla de oro:** una sola herramienta edita a la vez; **Git** es la única fuente de verdad.

## Reglas innegociables

1. **Idioma.** Toda comunicación y la UI, en **castellano**. El código (variables,
   funciones, rutas) en **inglés**.
2. **API de solo lectura.** No borrar música, no mover ficheros, no sobrescribir tags
   de audio. La deduplicación **expone**, nunca borra.
3. **Sin dependencias nuevas** salvo que sean imprescindibles y estén justificadas.
   Runtime en `requirements.txt`; tests en `requirements-dev.txt`.
4. **Nunca** versionar `.env` ni secretos (`api_connections.json`). Ya están en `.gitignore`.
5. **Un objetivo por rama y por PR.** Rama con prefijo (`feat/`, `fix/`, `docs/`,
   `refactor/`). El PR se abre en **draft** contra `main`.
6. **Plan antes de código.** Propón un plan corto y espera el OK antes de editar.
7. **Verde antes de merge.** `pytest` en verde y `py_compile` sin errores. Si añades
   servicio o endpoint, **añade test**.
8. **Cambios mínimos y localizados.** No reescribir la UI ni módulos enteros por un
   cambio pequeño.

## Arquitectura (resumen)

- `app/main.py` — FastAPI: routers, CORS, handler de errores de Discogs.
- `app/cabin.py` — sirve la web en `/` + `/api/music/library`, `/library/stats`, `/stream`.
- `app/static/index.html` — web mobile-first/tablet (vanilla, sin dependencias).
- `app/core/config.py` — `settings` (rutas, credenciales, puerto, multi-ruta).
- `app/connectors/discogs_client.py` — cliente Discogs + caché SQLite + excepciones tipadas.
- `app/routers/` — `health.py`, `music.py`, `discogs.py`.
- `app/services/` — `matcher.py`, `music_library.py`, `indexer.py`.

## Comandos

```bash
python -m pytest -q                          # tests
python -m py_compile $(git ls-files '*.py')  # compila
python index_music.py                        # indexa la biblioteca
# Web local: ./run_api.ps1  →  http://127.0.0.1:8765/  (Swagger en /docs)
```

## Antes de dar una tarea por terminada

- [ ] Se cumple el objetivo (uno solo) y nada fuera de él.
- [ ] `pytest` en verde y `py_compile` limpio.
- [ ] Sin dependencias nuevas no justificadas.
- [ ] `ROADMAP.md` actualizado si procede.
- [ ] PR en **draft** con resumen claro de qué cambia y por qué.

## Reparto de roles

- **Claude Code** (agente principal): planifica, implementa y abre PRs. Tiene dos
  subagentes de proyecto en `.claude/agents/`: **`musicbox-dev`** (implementa cambios) y
  **`musicbox-reviewer`** (revisa diffs, solo lectura).
- **Codex** (segunda opinión): revisa diffs y propone alternativas puntuales; lee este
  `AGENTS.md` como sus directrices.
- **Regla:** una sola herramienta edita un archivo a la vez. **Git/GitHub** es la única
  fuente de verdad.
