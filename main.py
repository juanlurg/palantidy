import argparse
import sys
import uvicorn
from src.config import HOST, PORT, DB_PATH
from src.sync import sync_moria_database

def main():
    parser = argparse.ArgumentParser(description="Palantidy - Stremio Addon for Palantir Catalog")
    parser.add_argument("--sync", action="store_true", help="Download/update the Moria database from GitHub")
    parser.add_argument("--force-sync", action="store_true", help="Force re-download Moria database even if present")
    parser.add_argument("--host", default=HOST, help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=PORT, help="Port to bind to (default: 7000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    if args.sync or args.force_sync:
        print("[Palantidy] Running database sync...")
        success = sync_moria_database(force=args.force_sync)
        if not success:
            sys.exit(1)
        print("[Palantidy] Sync finished successfully.")
        return

    # Check database presence before starting server
    import os
    if not os.path.exists(DB_PATH):
        print(f"[Palantidy] Database not found at {DB_PATH}. Syncing now...")
        sync_moria_database(force=False)

    print(f"\n=======================================================")
    print(f"  🪄 PALANTIDY - STREMIO ADDON IS STARTING")
    print(f"  Web UI / Config: http://localhost:{args.port}")
    print(f"  Stremio Addon:   stremio://localhost:{args.port}/manifest.json")
    print(f"=======================================================\n")

    uvicorn.run(
        "src.addon:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        proxy_headers=True,
        forwarded_allow_ips="*"
    )

if __name__ == "__main__":
    main()
