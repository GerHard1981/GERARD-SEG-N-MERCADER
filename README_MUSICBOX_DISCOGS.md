# MusicBox Discogs API

App corregida: la integración principal es Discogs, no Discord.

## Rutas base

- Música principal: `C:\Users\segun\Google Drive\Music_Master`
- MusicBox: `C:\Users\segun\Google Drive\MUSIC_BOX`
- App: `C:\Users\segun\Google Drive\MUSIC_BOX\APP\musicbox_discogs_api`

## Configurar Discogs

1. Entra en Discogs.
2. Ve a Settings > Developers.
3. Genera un User Token.
4. Edita el archivo `.env` de esta app.
5. Pega el token en `DISCOGS_TOKEN=`.

No pegues el token en ChatGPT.

## Ejecutar

```powershell
cd "$env:USERPROFILE\Google Drive\MUSIC_BOX\APP\musicbox_discogs_api"
.\run_api.ps1
```

Después abre:

```text
http://127.0.0.1:8765/docs
```

## Endpoints clave

- `GET /health`
- `GET /api/music/summary`
- `GET /api/music/files`
- `GET /api/discogs/config`
- `GET /api/discogs/search?q=Scooter&type=release`
- `GET /api/discogs/releases/{release_id}`
- `POST /api/discogs/match-file`
- `POST /api/discogs/match-folder`

## Seguridad

- No borra música.
- No mueve música.
- No sobrescribe tags de audio.
- Solo lee archivos y consulta Discogs.
- Los matches quedan guardados en SQLite local.
