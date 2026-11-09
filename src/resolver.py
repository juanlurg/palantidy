import urllib.request
import urllib.parse
import json
from typing import Optional, Dict, Any

class DebridResolver:
    @staticmethod
    def unrestrict_realdebrid(url: str, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Unrestricts a hoster link using Real-Debrid API.
        POST https://api.real-debrid.com/rest/1.0/unrestrict/link
        """
        endpoint = "https://api.real-debrid.com/rest/1.0/unrestrict/link"
        data = urllib.parse.urlencode({"link": url}).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data, method="POST")
        req.add_header("Authorization", f"Bearer {api_key}")
        req.add_header("User-Agent", "Palantidy/1.0")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                return {
                    "download_url": res_data.get("download"),
                    "filename": res_data.get("filename"),
                    "filesize": res_data.get("filesize"),
                    "streamable": res_data.get("streamable", 1)
                }
        except Exception as e:
            print(f"[Resolver] Real-Debrid unrestrict error for {url}: {e}")
            return None

    @staticmethod
    def unrestrict_alldebrid(url: str, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Unrestricts a hoster link using AllDebrid API.
        GET https://api.alldebrid.com/v4/link/unlock
        """
        params = urllib.parse.urlencode({
            "agent": "Palantidy",
            "apikey": api_key,
            "link": url
        })
        endpoint = f"https://api.alldebrid.com/v4/link/unlock?{params}"
        req = urllib.request.Request(endpoint, headers={"User-Agent": "Palantidy/1.0"})

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                if res_data.get("status") == "success":
                    data = res_data.get("data", {})
                    return {
                        "download_url": data.get("link"),
                        "filename": data.get("filename"),
                        "filesize": data.get("filesize")
                    }
        except Exception as e:
            print(f"[Resolver] AllDebrid unrestrict error for {url}: {e}")
            return None

    @staticmethod
    def unrestrict_1fichier(url: str, api_token: str) -> Optional[Dict[str, Any]]:
        """
        Direct 1fichier download link generation via their official API.
        POST https://api.1fichier.com/v1/download/get_token.cgi
        """
        endpoint = "https://api.1fichier.com/v1/download/get_token.cgi"
        payload = json.dumps({"url": url}).encode("utf-8")
        req = urllib.request.Request(endpoint, data=payload, method="POST")
        req.add_header("Authorization", f"Bearer {api_token}")
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                if res_data.get("status") == "OK":
                    return {
                        "download_url": res_data.get("url"),
                        "filename": res_data.get("filename", "video.mp4")
                    }
        except Exception as e:
            print(f"[Resolver] 1fichier direct unrestrict error: {e}")
            return None
