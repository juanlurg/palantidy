import sqlite3
import os
from typing import List, Dict, Optional, Any
from .config import DB_PATH
from .crypto import decrypt_palantir_url

class MoriaDatabase:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._ensure_indexes()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_indexes(self):
        """Creates high-performance indexes if they don't exist yet."""
        if not os.path.exists(self.db_path):
            return
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("CREATE INDEX IF NOT EXISTS idx_enlaces_pelis_tmdb ON enlaces_pelis(tmdb);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_enlaces_series_tmdb ON enlaces_series(tmdb, temporada, episodio);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_pelis_tmdb ON pelis(tmdb);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_series_tmdb ON series(tmdb);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_pelis_titulo ON pelis(titulo);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_series_titulo ON series(titulo);")
                conn.commit()
        except Exception as e:
            print(f"[Database] Warning ensuring indexes: {e}")

    def get_movie_links(self, tmdb_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves and decrypts all available links for a given TMDb movie ID.
        """
        query = """
            SELECT link, calidad, audio, info, updated 
            FROM enlaces_pelis 
            WHERE tmdb = ?
            ORDER BY 
                CASE 
                    WHEN calidad LIKE '%4K%' OR calidad LIKE '%UHD%' OR calidad LIKE '%DV%' THEN 1
                    WHEN calidad LIKE '%1080%' THEN 2
                    WHEN calidad LIKE '%720%' THEN 3
                    ELSE 4
                END
        """
        results = []
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (tmdb_id,))
            rows = cur.fetchall()
            for r in rows:
                decrypted_url = decrypt_palantir_url(r["link"])
                if decrypted_url:
                    results.append({
                        "url": decrypted_url,
                        "calidad": r["calidad"] or "HD",
                        "audio": r["audio"] or "esp",
                        "info": r["info"] or "",
                        "updated": r["updated"],
                        "tmdb": tmdb_id
                    })
        return results

    def get_series_links(self, tmdb_id: int, season: int, episode: int) -> List[Dict[str, Any]]:
        """
        Retrieves and decrypts all available links for a given TV show episode.
        """
        query = """
            SELECT link, calidad, audio, info, updated 
            FROM enlaces_series 
            WHERE tmdb = ? AND temporada = ? AND episodio = ?
            ORDER BY 
                CASE 
                    WHEN calidad LIKE '%4K%' OR calidad LIKE '%UHD%' OR calidad LIKE '%DV%' THEN 1
                    WHEN calidad LIKE '%1080%' THEN 2
                    WHEN calidad LIKE '%720%' THEN 3
                    ELSE 4
                END
        """
        results = []
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (tmdb_id, season, episode))
            rows = cur.fetchall()
            for r in rows:
                decrypted_url = decrypt_palantir_url(r["link"])
                if decrypted_url:
                    results.append({
                        "url": decrypted_url,
                        "calidad": r["calidad"] or "HD",
                        "audio": r["audio"] or "esp",
                        "info": r["info"] or "",
                        "updated": r["updated"],
                        "tmdb": tmdb_id,
                        "season": season,
                        "episode": episode
                    })
        return results

    def get_movie_meta(self, tmdb_id: int) -> Optional[Dict[str, Any]]:
        query = "SELECT tmdb, titulo, plot, poster, fondo, fecha, rating FROM pelis WHERE tmdb = ?"
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (tmdb_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
        return None

    def get_series_meta(self, tmdb_id: int) -> Optional[Dict[str, Any]]:
        query = "SELECT tmdb, titulo, plot, poster, fondo, fecha, rating FROM series WHERE tmdb = ?"
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (tmdb_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
        return None

    def search(self, text: str, limit: int = 15) -> Dict[str, List[Dict[str, Any]]]:
        pattern = f"%{text}%"
        movies, series = [], []
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT tmdb, titulo, fecha, poster, rating FROM pelis WHERE titulo LIKE ? LIMIT ?", (pattern, limit))
            movies = [dict(r) for r in cur.fetchall()]
            
            cur.execute("SELECT tmdb, titulo, fecha, poster, rating FROM series WHERE titulo LIKE ? LIMIT ?", (pattern, limit))
            series = [dict(r) for r in cur.fetchall()]
        return {"movies": movies, "series": series}

    def get_stats(self) -> Dict[str, Any]:
        if not os.path.exists(self.db_path):
            return {"status": "Database not found"}
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM pelis")
            pelis_count = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM series")
            series_count = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM enlaces_pelis")
            enlaces_pelis_count = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM enlaces_series")
            enlaces_series_count = cur.fetchone()[0]
            cur.execute("SELECT version, version_addon, mensaje_inicial FROM version LIMIT 1")
            v_row = cur.fetchone()
            v_info = dict(v_row) if v_row else {}

        return {
            "movies": pelis_count,
            "series": series_count,
            "movie_links": enlaces_pelis_count,
            "series_links": enlaces_series_count,
            "version": v_info
        }
