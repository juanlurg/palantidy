import urllib.request
import base64
import zipfile
import json
import os
import sqlite3
from pathlib import Path
from .config import DB_PATH, ZIP_HEADER_B64, GITHUB_REPO

META_SYNC_PATH = str(Path(DB_PATH).parent / "last_sync.json")

def get_latest_remote_commit() -> dict:
    """Fetches the latest commit metadata from GitHub repository."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/commits?page=1&per_page=1"
    req = urllib.request.Request(url, headers={"User-Agent": "Palantidy/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and isinstance(data, list):
                commit = data[0]
                return {
                    "sha": commit.get("sha", ""),
                    "date": commit.get("commit", {}).get("committer", {}).get("date", "")
                }
    except Exception as e:
        print(f"[Sync] Warning checking GitHub commits: {e}")
    return {}

def get_local_sync_meta() -> dict:
    if os.path.exists(META_SYNC_PATH):
        try:
            with open(META_SYNC_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_local_sync_meta(meta: dict):
    try:
        with open(META_SYNC_PATH, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
    except Exception as e:
        print(f"[Sync] Warning saving sync meta: {e}")

def sync_moria_database(force: bool = False, output_path: str = DB_PATH) -> bool:
    """
    Downloads and extracts the latest Moria SQLite database from the official Palantir repository.
    Only downloads if a newer commit exists on GitHub (unless force=True).
    """
    remote_meta = get_latest_remote_commit()
    local_meta = get_local_sync_meta()

    db_exists = os.path.exists(output_path)
    
    # Check if we already have the latest commit
    if db_exists and not force and remote_meta.get("sha") and remote_meta.get("sha") == local_meta.get("sha"):
        print(f"[Sync] Database is already up to date (Commit: {remote_meta.get('sha')[:8]} from {remote_meta.get('date')}).")
        return True

    print(f"[Sync] Checking for latest Moria database from {GITHUB_REPO}...")
    
    # Check current contents in GitHub repo
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents"
    req = urllib.request.Request(api_url, headers={"User-Agent": "Palantidy/1.0"})
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            contents = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[Sync] Warning fetching GitHub contents: {e}")
        contents = []

    target_file = None
    for item in contents:
        name = item.get("name", "")
        if name.startswith("moria_") and name.endswith(".zm3"):
            target_file = item
            break

    if not target_file:
        download_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/moria_3_3_11.zm3"
        filename = "moria_3_3_11.zm3"
    else:
        download_url = target_file.get("download_url")
        filename = target_file.get("name")

    print(f"[Sync] Downloading {filename} from {download_url}...")
    temp_zip = str(Path(output_path).parent / "temp_moria.zip")
    temp_db = str(Path(output_path).parent / "temp_moria.db")
    header = base64.b64decode(ZIP_HEADER_B64)

    try:
        req_dl = urllib.request.Request(download_url, headers={"User-Agent": "Palantidy/1.0"})
        with urllib.request.urlopen(req_dl, timeout=180) as resp, open(temp_zip, "wb") as f:
            f.write(header)
            downloaded = 0
            while chunk := resp.read(1024 * 1024):
                f.write(chunk)
                downloaded += len(chunk)
                print(f"[Sync] Downloaded {downloaded / (1024*1024):.1f} MB", end="\r")
        print("\n[Sync] Download complete! Unpacking database...")

        with zipfile.ZipFile(temp_zip, "r") as zf:
            with zf.open("settings.xml") as src, open(temp_db, "wb") as dst:
                while chunk := src.read(512 * 1024):
                    dst.write(chunk)

        # Build indexes on temp_db before atomically replacing
        with sqlite3.connect(temp_db) as conn:
            cur = conn.cursor()
            cur.execute("CREATE INDEX IF NOT EXISTS idx_enlaces_pelis_tmdb ON enlaces_pelis(tmdb);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_enlaces_series_tmdb ON enlaces_series(tmdb, temporada, episodio);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pelis_tmdb ON pelis(tmdb);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_series_tmdb ON series(tmdb);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pelis_titulo ON pelis(titulo);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_series_titulo ON series(titulo);")
            conn.commit()

        # Atomic replace
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass
        os.replace(temp_db, output_path)

        # Save metadata
        if remote_meta:
            save_local_sync_meta(remote_meta)

        print(f"[Sync] Successfully updated {output_path} ({os.path.getsize(output_path) / (1024*1024):.1f} MB)")
        return True
    except Exception as e:
        print(f"[Sync] Error syncing Moria database: {e}")
        return False
    finally:
        for tmp in (temp_zip, temp_db):
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except Exception:
                    pass
