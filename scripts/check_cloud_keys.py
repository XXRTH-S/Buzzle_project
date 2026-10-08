"""Read-only provider checks. Never prints keys, response bodies or exception details."""
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from dotenv import dotenv_values

env = dotenv_values(Path(__file__).resolve().parents[1] / ".env")


def check(label, url, headers):
    headers = {"User-Agent": "Buzzle-Readiness/1.0", **headers}
    try:
        with urlopen(Request(url, headers=headers), timeout=20) as response:
            payload = json.load(response)
        print(f"{label}: HTTP 200")
        return payload
    except HTTPError as error:
        print(f"{label}: HTTP {error.code}")
    except Exception:
        print(f"{label}: unavailable (network or invalid response)")
    return None


for label, field, endpoint in (
    ("Groq authentication", "GROQ_API_KEY", "https://api.groq.com/openai/v1/models"),
    ("OpenRouter authentication", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1/key"),
):
    key = env.get(field, "")
    if key:
        check(label, endpoint, {"Authorization": f"Bearer {key}"})
    else:
        print(f"{label}: missing")

url = (env.get("SUPABASE_URL") or "").rstrip("/")
parsed = urlparse(url)
secret = env.get("SUPABASE_SECRET_KEY") or ""
if (parsed.scheme == "https" and parsed.hostname == "ptklhaxkhluqmcpjyrma.supabase.co"
        and not parsed.username and not parsed.port and not parsed.path and secret):
    headers = {"apikey": secret}
    if not secret.startswith("sb_secret_"):
        headers["Authorization"] = f"Bearer {secret}"
    buckets = check("Supabase bucket access", url + "/storage/v1/bucket", headers)
    if isinstance(buckets, list):
        selected = env.get("SUPABASE_STORAGE_BUCKET")
        found = next((b for b in buckets if b.get("id") == selected), None)
        print("Configured bucket: " + ("found" if found else "not found"))
        if found:
            print("Bucket private: " + str(not found.get("public", False)))
        # User-confirmed name only; do not disclose unrelated bucket metadata.
        print("Screenshot bucket exists: " + str(any(b.get("id") == "XXRTH-S's Buzzle" for b in buckets)))
else:
    print("Supabase: missing secret or unexpected project URL; not contacted")
print("Inngest: presence only; keys require app integration to validate")
