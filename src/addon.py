import json
import base64
import urllib.parse
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any

from .config import REALDEBRID_API_KEY, ALLDEBRID_API_KEY, SYNC_INTERVAL_HOURS
from .database import MoriaDatabase
from .id_mapper import IdMapper
from .resolver import DebridResolver
from .sync import sync_moria_database, get_local_sync_meta

async def background_sync_task():
    """Periodically checks and updates the Moria database in the background."""
    while True:
        try:
            # Wait interval before running (e.g. 12 hours)
            await asyncio.sleep(SYNC_INTERVAL_HOURS * 3600)
            print(f"[AutoSync] Running scheduled database check (Interval: {SYNC_INTERVAL_HOURS}h)...")
            sync_moria_database(force=False)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[AutoSync] Error in periodic sync task: {e}")
            await asyncio.sleep(600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background sync task
    sync_task = asyncio.create_task(background_sync_task())
    yield
    # Shutdown: Cancel background sync task
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="Palantidy", description="Stremio Addon for Palantir Catalog", version="1.0.0", lifespan=lifespan)

# Enable CORS for all origins (Required for Stremio Web and Desktop/Android TV apps)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = MoriaDatabase()
mapper = IdMapper()

def parse_user_config(config_str: Optional[str]) -> Dict[str, Any]:
    """Parses optional configuration string from the URL path."""
    if not config_str:
        return {
            "provider": "realdebrid" if REALDEBRID_API_KEY else ("alldebrid" if ALLDEBRID_API_KEY else "none"),
            "token": REALDEBRID_API_KEY or ALLDEBRID_API_KEY or "",
            "audio_filter": "all"
        }
    
    try:
        # Try base64 json decode
        decoded = base64.urlsafe_b64decode(config_str.encode()).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        pass

    try:
        # Try raw json decode
        return json.loads(urllib.parse.unquote(config_str))
    except Exception:
        pass

    return {
        "provider": "realdebrid" if REALDEBRID_API_KEY else ("alldebrid" if ALLDEBRID_API_KEY else "none"),
        "token": REALDEBRID_API_KEY or ALLDEBRID_API_KEY or "",
        "audio_filter": "all"
    }

def get_manifest():
    return {
        "id": "org.palantidy.addon",
        "version": "1.0.0",
        "name": "Palantidy (Palantir)",
        "description": "Enlaces en Castellano (4K / 1080p / Debrid) desde el catálogo de Palantir",
        "logo": "https://raw.githubusercontent.com/palantirsource/palantir/refs/heads/main/icon.png",
        "resources": ["stream"],
        "types": ["movie", "series"],
        "idPrefixes": ["tt", "tmdb:"],
        "catalogs": [],
        "behaviorHints": {
            "configurable": True,
            "configurationRequired": False
        }
    }

@app.get("/manifest.json")
async def manifest_default():
    return JSONResponse(get_manifest())

@app.get("/{config}/manifest.json")
async def manifest_configured(config: str):
    return JSONResponse(get_manifest())

@app.get("/stream/{media_type}/{item_id}.json")
@app.get("/{config}/stream/{media_type}/{item_id}.json")
async def stream_handler(media_type: str, item_id: str, request: Request, config: Optional[str] = None):
    """
    Handles Stremio stream requests.
    item_id can be 'tt1234567' or 'tt1234567:1:1' or 'tmdb:1234'
    """
    cfg = parse_user_config(config)
    provider = cfg.get("provider", "realdebrid")
    token = cfg.get("token", "")

    # Clean extension if passed as .json
    clean_id = item_id.replace(".json", "")
    tmdb_id, season, episode = mapper.get_tmdb_id(media_type, clean_id)

    if not tmdb_id:
        return JSONResponse({"streams": []})

    # Retrieve links from Moria database
    if media_type == "series" and season is not None and episode is not None:
        raw_links = db.get_series_links(tmdb_id, season, episode)
    else:
        raw_links = db.get_movie_links(tmdb_id)

    if not raw_links:
        return JSONResponse({"streams": []})

    base_url = str(request.base_url).rstrip("/")
    streams = []

    # Format streams for Stremio
    for link_item in raw_links:
        url = link_item["url"]
        calidad = link_item.get("calidad", "HD")
        audio = link_item.get("audio", "esp")
        info = link_item.get("info", "")

        # Format audio tags (e.g. 'esp,eng' -> 'Castellano / Dual')
        audio_label = "Castellano" if "esp" in audio.lower() else audio.upper()
        if "eng" in audio.lower() and "esp" in audio.lower():
            audio_label = "Dual (Castellano/Inglés)"

        # Check audio filter if set
        if cfg.get("audio_filter") == "esp_only" and "esp" not in audio.lower():
            continue

        # Build lazy-resolution URL
        resolve_params = urllib.parse.urlencode({
            "url": url,
            "provider": provider,
            "token": token
        })
        play_url = f"{base_url}/resolve?{resolve_params}"

        server_label = "1fichier" if "1fichier" in url else "Direct"
        provider_badge = f"[{provider.upper()}]" if provider != "none" else ""

        title_lines = [
            f"🎬 {calidad} | 🔊 {audio_label}",
            f"💾 {server_label} {provider_badge} {info}".strip()
        ]

        streams.append({
            "name": f"Palantir {provider_badge}".strip(),
            "title": "\n".join(title_lines),
            "url": play_url,
            "behaviorHints": {
                "bingeGroup": f"palantidy-{calidad}-{audio}"
            }
        })

    return JSONResponse({"streams": streams})

@app.get("/resolve")
async def resolve_handler(url: str, provider: str = "realdebrid", token: str = ""):
    """
    Lazy link resolver: Resolves the 1fichier link to a direct streamable MP4/MKV
    when the user presses PLAY, and redirects the video player (ExoPlayer).
    """
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL parameter")

    # If no provider is configured, check global environment variables
    if not token:
        if provider == "realdebrid":
            token = REALDEBRID_API_KEY
        elif provider == "alldebrid":
            token = ALLDEBRID_API_KEY

    # 1. Real-Debrid
    if provider == "realdebrid" and token:
        result = DebridResolver.unrestrict_realdebrid(url, token)
        if result and result.get("download_url"):
            return RedirectResponse(url=result["download_url"], status_code=302)

    # 2. AllDebrid
    if provider == "alldebrid" and token:
        result = DebridResolver.unrestrict_alldebrid(url, token)
        if result and result.get("download_url"):
            return RedirectResponse(url=result["download_url"], status_code=302)

    # 3. Direct 1fichier with user token
    if provider == "1fichier" and token:
        result = DebridResolver.unrestrict_1fichier(url, token)
        if result and result.get("download_url"):
            return RedirectResponse(url=result["download_url"], status_code=302)

    # Fallback: Redirect directly to the hoster URL
    return RedirectResponse(url=url, status_code=302)

@app.get("/", response_class=HTMLResponse)
@app.get("/configure", response_class=HTMLResponse)
async def configure_page(request: Request):
    """Modern web configuration UI for easy 1-click installation into Stremio."""
    stats = db.get_stats()
    base_url = str(request.base_url).rstrip("/")
    stremio_base = base_url.replace("http://", "stremio://").replace("https://", "stremio://")

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Palantidy - Addon de Stremio</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg: #0f1015;
                --card: #181920;
                --accent: #6c5ce7;
                --accent-hover: #5849c7;
                --text: #ffffff;
                --text-muted: #8e92a4;
                --border: #272935;
                --success: #00b894;
            }}
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                font-family: 'Inter', sans-serif;
                background-color: var(--bg);
                color: var(--text);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .container {{
                background: var(--card);
                border: 1px solid var(--border);
                border-radius: 16px;
                padding: 40px;
                max-width: 520px;
                width: 100%;
                box-shadow: 0 20px 40px rgba(0,0,0,0.4);
            }}
            .logo {{
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 8px;
            }}
            .logo h1 {{ font-size: 26px; font-weight: 700; color: #a29bfe; }}
            .subtitle {{ color: var(--text-muted); font-size: 14px; margin-bottom: 24px; }}
            .stats-bar {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px;
                background: #12131a;
                padding: 14px;
                border-radius: 10px;
                margin-bottom: 24px;
                border: 1px solid var(--border);
            }}
            .stat-item {{ text-align: center; }}
            .stat-val {{ font-size: 18px; font-weight: 700; color: var(--success); }}
            .stat-lbl {{ font-size: 12px; color: var(--text-muted); }}
            .form-group {{ margin-bottom: 20px; }}
            label {{ display: block; font-size: 13px; font-weight: 600; margin-bottom: 8px; }}
            select, input {{
                width: 100%;
                background: #12131a;
                border: 1px solid var(--border);
                color: var(--text);
                padding: 12px 14px;
                border-radius: 8px;
                font-size: 14px;
                outline: none;
                transition: border-color 0.2s;
            }}
            select:focus, input:focus {{ border-color: var(--accent); }}
            .btn {{
                display: block;
                width: 100%;
                background: var(--accent);
                color: #fff;
                border: none;
                padding: 14px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                text-align: center;
                text-decoration: none;
                transition: background 0.2s;
            }}
            .btn:hover {{ background: var(--accent-hover); }}
            .info-box {{
                margin-top: 20px;
                font-size: 12px;
                color: var(--text-muted);
                line-height: 1.5;
                background: rgba(108, 92, 231, 0.08);
                border: 1px solid rgba(108, 92, 231, 0.2);
                padding: 12px;
                border-radius: 8px;
            }}
            .manifest-url {{
                word-break: break-all;
                background: #101117;
                padding: 10px;
                border-radius: 6px;
                font-family: monospace;
                font-size: 12px;
                margin-top: 10px;
                color: #a29bfe;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">
                <h1>Palantidy 🪄</h1>
            </div>
            <p class="subtitle">Conecta todo el catálogo de Palantir directamente con Stremio.</p>
            
            <div class="stats-bar">
                <div class="stat-item">
                    <div class="stat-val">{stats.get('movies', 0):,}</div>
                    <div class="stat-lbl">Películas indexadas</div>
                </div>
                <div class="stat-item">
                    <div class="stat-val">{stats.get('series_links', 0):,}</div>
                    <div class="stat-lbl">Enlaces de Series</div>
                </div>
            </div>

            <div class="form-group">
                <label>Servicio Debrid (Recomendado para streaming instantáneo):</label>
                <select id="provider" onchange="updateInstallUrl()">
                    <option value="realdebrid">Real-Debrid (Recomendado)</option>
                    <option value="alldebrid">AllDebrid</option>
                    <option value="1fichier">1fichier (API Token)</option>
                    <option value="none">Sin resolver (Solo enlaces directos)</option>
                </select>
            </div>

            <div class="form-group">
                <label>API Key / Token del Debrid:</label>
                <input type="password" id="token" placeholder="Pega tu API Key aquí..." oninput="updateInstallUrl()" value="{REALDEBRID_API_KEY or ALLDEBRID_API_KEY}">
            </div>

            <div class="form-group">
                <label>Filtro de Idioma:</label>
                <select id="audio_filter" onchange="updateInstallUrl()">
                    <option value="all">Todos los audios (Castellano, Dual, etc.)</option>
                    <option value="esp_only">Solo Castellano</option>
                </select>
            </div>

            <a id="installBtn" class="btn" href="#">Instalar en Stremio</a>

            <div class="info-box">
                <strong>¿Cómo instalarlo en Google TV?</strong><br>
                1. Configura tus opciones arriba y haz clic en "Instalar en Stremio" desde cualquier dispositivo con tu cuenta de Stremio abierta.<br>
                2. ¡Listo! El addon se sincronizará automáticamente en tu Google TV.
                <div id="manifestDisplay" class="manifest-url"></div>
            </div>
        </div>

        <script>
            const BASE_HTTP = "{base_url}";
            const BASE_STREMIO = "{stremio_base}";

            function updateInstallUrl() {{
                const provider = document.getElementById("provider").value;
                const token = document.getElementById("token").value.trim();
                const audioFilter = document.getElementById("audio_filter").value;

                const cfgObj = {{ provider: provider, token: token, audio_filter: audioFilter }};
                const cfgB64 = btoa(JSON.stringify(cfgObj)).replace(/\\+/g, '-').replace(/\\//g, '_').replace(/=+$/, '');

                const installUrl = BASE_STREMIO + "/" + cfgB64 + "/manifest.json";
                const httpUrl = BASE_HTTP + "/" + cfgB64 + "/manifest.json";

                document.getElementById("installBtn").href = installUrl;
                document.getElementById("manifestDisplay").innerText = "URL del Addon: " + httpUrl;
            }}

            updateInstallUrl();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.post("/api/sync")
async def trigger_manual_sync(force: bool = False):
    """Allows triggering a manual database sync from web UI or curl."""
    success = sync_moria_database(force=force)
    return {"success": success, "sync_meta": get_local_sync_meta()}

@app.get("/api/search")
async def api_search(q: str):
    """Instant search endpoint for testing queries."""
    if not q:
        return {"movies": [], "series": []}
    return db.search(q)

@app.get("/api/stats")
async def api_stats():
    return db.get_stats()
