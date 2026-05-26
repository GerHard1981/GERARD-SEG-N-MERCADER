from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from app.core.config import settings


class DiscogsError(RuntimeError):
    pass


class DiscogsClient:
    """Small Discogs REST client with local SQLite cache and safe headers."""

    def __init__(self) -> None:
        self.base_url = settings.discogs_api_base
        self.cache_db = settings.discogs_cache_db
        self.ttl = settings.discogs_cache_ttl_seconds
        self.session = requests.Session()
        self._last_request_at = 0.0
        self._init_cache()

    def _init_cache(self) -> None:
        self.cache_db.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.cache_db) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS http_cache (
                    cache_key TEXT PRIMARY KEY,
                    created_at REAL NOT NULL,
                    method TEXT NOT NULL,
                    url TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    status_code INTEGER NOT NULL,
                    headers_json TEXT NOT NULL,
                    body TEXT NOT NULL
                )
                """
            )
            con.commit()

    def _headers(self) -> Dict[str, str]:
        headers = {
            "User-Agent": settings.discogs_user_agent,
            "Accept": "application/json",
        }
        if settings.discogs_token:
            headers["Authorization"] = f"Discogs token={settings.discogs_token}"
        return headers

    @staticmethod
    def _cache_key(method: str, url: str, params: Dict[str, Any]) -> str:
        payload = json.dumps({"method": method, "url": url, "params": params}, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _get_cached(self, key: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.cache_db) as con:
            row = con.execute(
                "SELECT created_at, status_code, headers_json, body FROM http_cache WHERE cache_key=?",
                (key,),
            ).fetchone()
        if not row:
            return None
        created_at, status_code, headers_json, body = row
        if time.time() - float(created_at) > self.ttl:
            return None
        return {
            "cached": True,
            "status_code": int(status_code),
            "headers": json.loads(headers_json),
            "data": json.loads(body),
        }

    def _save_cache(self, key: str, method: str, url: str, params: Dict[str, Any], response: requests.Response) -> None:
        try:
            body = response.text
            json.loads(body)
        except Exception:
            return
        with sqlite3.connect(self.cache_db) as con:
            con.execute(
                """
                INSERT OR REPLACE INTO http_cache
                (cache_key, created_at, method, url, params_json, status_code, headers_json, body)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    time.time(),
                    method,
                    url,
                    json.dumps(params, sort_keys=True, default=str),
                    response.status_code,
                    json.dumps(dict(response.headers)),
                    body,
                ),
            )
            con.commit()

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, use_cache: bool = True) -> Dict[str, Any]:
        params = {k: v for k, v in (params or {}).items() if v not in (None, "", [])}
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        key = self._cache_key(method, url, params)

        if use_cache and method.upper() == "GET":
            cached = self._get_cached(key)
            if cached is not None:
                return cached

        # Gentle local pacing. Discogs also enforces its own rate limit.
        elapsed = time.time() - self._last_request_at
        if elapsed < 0.25:
            time.sleep(0.25 - elapsed)

        response = self.session.request(method, url, params=params, headers=self._headers(), timeout=30)
        self._last_request_at = time.time()

        rate_headers = {
            "X-Discogs-Ratelimit": response.headers.get("X-Discogs-Ratelimit"),
            "X-Discogs-Ratelimit-Used": response.headers.get("X-Discogs-Ratelimit-Used"),
            "X-Discogs-Ratelimit-Remaining": response.headers.get("X-Discogs-Ratelimit-Remaining"),
        }

        try:
            data = response.json()
        except Exception:
            data = {"raw": response.text}

        if response.status_code >= 400:
            return {
                "cached": False,
                "status_code": response.status_code,
                "headers": rate_headers,
                "error": data,
            }

        if use_cache and method.upper() == "GET":
            self._save_cache(key, method, url, params, response)

        return {
            "cached": False,
            "status_code": response.status_code,
            "headers": rate_headers,
            "data": data,
        }

    def config_status(self) -> Dict[str, Any]:
        return {
            "base_url": self.base_url,
            "token_configured": settings.token_configured,
            "user_agent": settings.discogs_user_agent,
            "cache_db": str(settings.discogs_cache_db),
            "matches_db": str(settings.matches_db),
        }

    def identity(self) -> Dict[str, Any]:
        return self._request("GET", "/oauth/identity", use_cache=False)

    def search(self, **params: Any) -> Dict[str, Any]:
        return self._request("GET", "/database/search", params=params)

    def release(self, release_id: int) -> Dict[str, Any]:
        return self._request("GET", f"/releases/{release_id}")

    def master(self, master_id: int) -> Dict[str, Any]:
        return self._request("GET", f"/masters/{master_id}")

    def artist(self, artist_id: int) -> Dict[str, Any]:
        return self._request("GET", f"/artists/{artist_id}")

    def label(self, label_id: int) -> Dict[str, Any]:
        return self._request("GET", f"/labels/{label_id}")

    def collection_folders(self, username: str) -> Dict[str, Any]:
        return self._request("GET", f"/users/{username}/collection/folders", use_cache=False)

    def collection_releases(self, username: str, folder_id: int = 0, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        return self._request(
            "GET",
            f"/users/{username}/collection/folders/{folder_id}/releases",
            params={"page": page, "per_page": per_page},
            use_cache=False,
        )

    def wants(self, username: str, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        return self._request("GET", f"/users/{username}/wants", params={"page": page, "per_page": per_page}, use_cache=False)


discogs_client = DiscogsClient()
