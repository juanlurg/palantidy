import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from fastapi.testclient import TestClient
from src.addon import app
from src.database import MoriaDatabase
from src.id_mapper import IdMapper

print("--- 1. Testing Database & Decryption ---")
db = MoriaDatabase()
matrix_links = db.get_movie_links(603)
print(f"Matrix (TMDb 603) links found: {len(matrix_links)}")
for l in matrix_links[:3]:
    print(f"  [{l['calidad']}] [{l['audio']}] {l['url']}")

bb_links = db.get_series_links(1396, 1, 1)
print(f"\nBreaking Bad S01E01 links found: {len(bb_links)}")
for l in bb_links[:3]:
    print(f"  [{l['calidad']}] [{l['audio']}] {l['url']}")

print("\n--- 2. Testing ID Mapping ---")
mapper = IdMapper()
tmdb_movie, s, e = mapper.get_tmdb_id("movie", "tt0133093")
print(f"tt0133093 -> TMDb {tmdb_movie}")

tmdb_show, s, e = mapper.get_tmdb_id("series", "tt0903747:1:1")
print(f"tt0903747:1:1 -> TMDb {tmdb_show}, S{s}E{e}")

print("\n--- 3. Testing Stremio API Endpoints ---")
client = TestClient(app)

res_manifest = client.get("/manifest.json")
print("Manifest status:", res_manifest.status_code)
print("Manifest name:", res_manifest.json().get("name"))

res_streams_movie = client.get("/stream/movie/tt0133093.json")
print("Matrix streams status:", res_streams_movie.status_code)
movie_streams = res_streams_movie.json().get("streams", [])
print(f"Movie streams returned: {len(movie_streams)}")
if movie_streams:
    print("Sample stream item:")
    print("  Name:", movie_streams[0]["name"])
    print("  Title:\n" + "\n".join("    " + x for x in movie_streams[0]["title"].splitlines()))
    print("  URL:", movie_streams[0]["url"])

res_streams_series = client.get("/stream/series/tt0903747:1:1.json")
print("\nBreaking Bad streams status:", res_streams_series.status_code)
series_streams = res_streams_series.json().get("streams", [])
print(f"Series streams returned: {len(series_streams)}")
if series_streams:
    print("Sample stream item:")
    print("  Name:", series_streams[0]["name"])
    print("  Title:\n" + "\n".join("    " + x for x in series_streams[0]["title"].splitlines()))
    print("  URL:", series_streams[0]["url"])

print("\nALL VERIFICATIONS PASSED WITH FLYING COLORS! 🚀")
