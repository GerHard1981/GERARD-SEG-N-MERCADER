"""MusicBox - Indexador de musica (CLI).

Escanea las raices configuradas (settings.music_master), lee tags con mutagen y
puebla el indice SQLite que consume /api/music/library. No mueve ni borra nada.

Uso:
    python index_music.py

La salida (SQLite) va a: <MUSICBOX_ROOT>/05_INDEXES/music_inventory.sqlite3
"""

from __future__ import annotations

import json

from app.services.indexer import build_index, default_scan_roots, index_db_path


def main() -> None:
    print("=" * 60)
    print("MUSICBOX - INDEXADOR DE MUSICA")
    print("=" * 60)
    print(f"SQLite destino: {index_db_path()}")
    print("Raices a escanear:")
    for root in default_scan_roots():
        print(f"  - {root}")
    print()

    stats = build_index()

    print(json.dumps(stats, indent=2, ensure_ascii=False, default=str))
    print()
    print(f"Listo: {stats['total']} tracks indexados en {stats['db_path']}")


if __name__ == "__main__":
    main()
