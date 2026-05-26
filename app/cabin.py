from __future__ import annotations
import os, re, sqlite3
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

from app.core.config import settings

router = APIRouter(tags=["web"])
USER = os.environ.get("USERPROFILE", str(Path.home()))
ALLOWED_ROOTS = [
    settings.music_master,
    settings.musicbox_root,
    Path(USER) / "OneDrive",
    Path(USER) / "Google Drive" / "Music_Master",
    Path("G:/Mi unidad/Music_Master"),
]
ALLOWED_EXTENSIONS = {".mp3",".wav",".flac",".aiff",".aif",".m4a",".ogg",".aac",".opus"}
MIME_TYPES = {".mp3":"audio/mpeg",".wav":"audio/wav",".flac":"audio/flac",".aiff":"audio/aiff",".aif":"audio/aiff",".m4a":"audio/mp4",".aac":"audio/aac",".ogg":"audio/ogg",".opus":"audio/opus"}
LIBRARY_DB = settings.musicbox_root / "05_INDEXES" / "music_inventory.sqlite3"
STATIC_DIR = Path(__file__).parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"

def is_path_allowed(path):
    try:
        resolved = path.resolve()
    except: return False
    for root in ALLOWED_ROOTS:
        try:
            resolved.relative_to(root.resolve()); return True
        except: continue
    return False

def parse_range(header, size):
    m = re.match(r"bytes=(\d+)-(\d*)", header)
    if not m: return 0, size-1
    s = int(m.group(1)); e = int(m.group(2)) if m.group(2) else size-1
    return s, min(e, size-1)

def open_db():
    if not LIBRARY_DB.exists(): return None
    conn = sqlite3.connect(str(LIBRARY_DB)); conn.row_factory = sqlite3.Row; return conn

@router.get("/", response_class=HTMLResponse)
async def serve_index():
    if not INDEX_HTML.exists():
        raise HTTPException(404, f"index.html not found at {INDEX_HTML}")
    return HTMLResponse(INDEX_HTML.read_text(encoding="utf-8"))

@router.get("/api/music/library")
async def list_library(q: Optional[str]=Query(None), limit: int=Query(500,ge=1,le=5000), offset: int=Query(0,ge=0)):
    conn = open_db()
    if conn is None:
        return {"tracks":[],"total":0,"indexed":False,"message":f"Run index_music.py to create {LIBRARY_DB}"}
    where, params = "", []
    if q:
        like = f"%{q}%"; where = " WHERE (artist LIKE ? OR title LIKE ? OR album LIKE ? OR filename LIKE ?)"; params = [like,like,like,like]
    c = conn.cursor()
    total = c.execute(f"SELECT COUNT(*) FROM tracks{where}", params).fetchone()[0]
    rows = c.execute(f"SELECT id,full_path,filename,extension,size_bytes,artist,title,album,year,genre,duration_seconds,bitrate FROM tracks{where} ORDER BY artist,album,title LIMIT ? OFFSET ?", params+[limit,offset]).fetchall()
    tracks = [{"id":r["id"],"path":r["full_path"],"filename":r["filename"],"extension":r["extension"],"artist":r["artist"] or "","title":r["title"] or r["filename"] or "(untitled)","album":r["album"] or "","year":r["year"] or "","genre":r["genre"] or "","duration_seconds":r["duration_seconds"],"bitrate":r["bitrate"]} for r in rows]
    conn.close()
    return {"tracks":tracks,"total":total,"limit":limit,"offset":offset,"indexed":True}

@router.get("/api/music/library/stats")
async def library_stats():
    conn = open_db()
    if conn is None: return {"indexed":False}
    c = conn.cursor()
    total = c.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
    gb = (c.execute("SELECT COALESCE(SUM(size_bytes),0) FROM tracks").fetchone()[0] or 0)/(1024**3)
    by_ext = {r[0]:r[1] for r in c.execute("SELECT extension,COUNT(*) FROM tracks GROUP BY extension ORDER BY 2 DESC").fetchall()}
    conn.close()
    return {"indexed":True,"total_tracks":total,"total_gb":round(gb,2),"by_extension":by_ext}

@router.get("/api/music/stream")
async def stream_audio(path: str, request: Request):
    fp = Path(path)
    if not is_path_allowed(fp): raise HTTPException(403,"Path not allowed")
    if not fp.exists(): raise HTTPException(404,"File not found")
    ext = fp.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS: raise HTTPException(415,f"Unsupported: {ext}")
    size = fp.stat().st_size
    mt = MIME_TYPES.get(ext,"application/octet-stream")
    rh = request.headers.get("range") or request.headers.get("Range")
    if not rh: return FileResponse(str(fp),media_type=mt,headers={"Accept-Ranges":"bytes"})
    s,e = parse_range(rh,size); length = e-s+1
    def gen(sp,nb,chunk=65536):
        with open(fp,"rb") as f:
            f.seek(sp); rem=nb
            while rem>0:
                d=f.read(min(chunk,rem))
                if not d: break
                rem-=len(d); yield d
    return StreamingResponse(gen(s,length),status_code=206,media_type=mt,headers={"Content-Range":f"bytes {s}-{e}/{size}","Accept-Ranges":"bytes","Content-Length":str(length),"Content-Type":mt})
