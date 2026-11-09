import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Database & Sync settings
DB_PATH = os.environ.get("PALANTIDY_DB_PATH", str(BASE_DIR / "moria.db"))
GITHUB_REPO = "Maniac2017/Mipal2025"
ZIP_HEADER_B64 = b"UEsDBBQAAAAIAKJchVngR+RlsfTRAQBwSwUMAAAAc2V0dGluZ3MueG1s"

# Server settings
HOST = os.environ.get("PALANTIDY_HOST", "0.0.0.0")
PORT = int(os.environ.get("PALANTIDY_PORT", "7000"))

# Sync settings
SYNC_INTERVAL_HOURS = int(os.environ.get("SYNC_INTERVAL_HOURS", "12"))

# Global default Debrid API Keys (optional; can also be configured per-user via Stremio URL)
REALDEBRID_API_KEY = os.environ.get("REALDEBRID_API_KEY", "")
ALLDEBRID_API_KEY = os.environ.get("ALLDEBRID_API_KEY", "")
DEBRIDLINK_API_KEY = os.environ.get("DEBRIDLINK_API_KEY", "")
