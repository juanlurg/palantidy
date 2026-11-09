import urllib.request
import json
import sqlite3
import re
from typing import Optional, Tuple
from .config import DB_PATH

class IdMapper:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._mem_cache = {}
        self._init_cache_table()

    def _init_cache_table(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS imdb_tmdb_cache (
                        imdb_id TEXT PRIMARY KEY,
                        tmdb_id INTEGER,
                        media_type TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.commit()
        except Exception as e:
            print(f"[IdMapper] Warning initializing cache table: {e}")

    def get_tmdb_id(self, media_type: str, raw_id: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """
        Parses raw Stremio ID and returns (tmdb_id, season, episode).
        Supports:
          - 'tmdb:12345'
          - 'tmdb:12345:1:2'
          - 'tt1234567'
          - 'tt1234567:1:2'
        """
        season = None
        episode = None
        parts = raw_id.split(":")

        # Parse season/episode if present (e.g. tt0903747:1:1 or tmdb:1396:1:1)
        if len(parts) >= 3 and parts[0] in ("tt", "tmdb"):
            # Format: tt:0903747:1:1 or tmdb:1396:1:1
            if parts[0] == "tmdb":
                tmdb_id = int(parts[1])
                season = int(parts[2])
                episode = int(parts[3])
                return tmdb_id, season, episode
            elif parts[0] == "tt":
                imdb_id = f"tt{parts[1]}"
                season = int(parts[2])
                episode = int(parts[3])
                tmdb_id = self._resolve_imdb_to_tmdb(media_type, imdb_id)
                return tmdb_id, season, episode

        if len(parts) == 3 and parts[0].startswith("tt"):
            # Format: tt0903747:1:1
            imdb_id = parts[0]
            season = int(parts[1])
            episode = int(parts[2])
            tmdb_id = self._resolve_imdb_to_tmdb(media_type, imdb_id)
            return tmdb_id, season, episode

        # Standalone movie / show ID
        if raw_id.startswith("tmdb:"):
            return int(raw_id.replace("tmdb:", "")), None, None

        if raw_id.startswith("tt"):
            tmdb_id = self._resolve_imdb_to_tmdb(media_type, raw_id)
            return tmdb_id, None, None

        return None, None, None

    def _resolve_imdb_to_tmdb(self, media_type: str, imdb_id: str) -> Optional[int]:
        # Check memory cache
        if imdb_id in self._mem_cache:
            return self._mem_cache[imdb_id]

        # Check DB cache
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT tmdb_id FROM imdb_tmdb_cache WHERE imdb_id = ?", (imdb_id,))
                row = cur.fetchone()
                if row and row[0]:
                    self._mem_cache[imdb_id] = row[0]
                    return row[0]
        except Exception:
            pass

        # Query Cinemeta API
        api_type = "series" if media_type == "series" else "movie"
        url = f"https://v3-cinemeta.strem.io/meta/{api_type}/{imdb_id}.json"
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                meta = data.get("meta", {})
                tmdb_id = meta.get("moviedb_id")
                if tmdb_id:
                    tmdb_id = int(tmdb_id)
                    self._mem_cache[imdb_id] = tmdb_id
                    self._save_to_cache(imdb_id, tmdb_id, media_type)
                    return tmdb_id
        except Exception as e:
            print(f"[IdMapper] Failed resolving {imdb_id} via Cinemeta: {e}")

        return None

    def _save_to_cache(self, imdb_id: str, tmdb_id: int, media_type: str):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO imdb_tmdb_cache (imdb_id, tmdb_id, media_type) VALUES (?, ?, ?)",
                    (imdb_id, tmdb_id, media_type)
                )
                conn.commit()
        except Exception as e:
            print(f"[IdMapper] Failed saving to cache: {e}")
