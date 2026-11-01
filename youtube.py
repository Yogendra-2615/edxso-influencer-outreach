"""Thin, error-tolerant wrapper over the YouTube Data API v3."""
import time
import requests
import config

BASE = "https://www.googleapis.com/youtube/v3/"

class QuotaExceeded(RuntimeError):
    pass

def get(endpoint, params, retries=3):
    if not config.YOUTUBE_API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY is not set (see .env.example)")
    params = {**params, "key": config.YOUTUBE_API_KEY}
    for attempt in range(retries):
        try:
            r = requests.get(BASE + endpoint, params=params, timeout=20)
        except requests.RequestException:
            time.sleep(2 ** attempt)
            continue
        if r.status_code == 200:
            return r.json()
        reason = ""
        try:
            reason = r.json()["error"]["errors"][0]["reason"]
        except Exception:
            pass
        if reason in ("quotaExceeded", "dailyLimitExceeded"):
            raise QuotaExceeded("YouTube API daily quota exhausted; resume tomorrow (state is saved).")
        if r.status_code in (429, 500, 502, 503):
            time.sleep(2 ** attempt)
            continue
        return {}          # 4xx other than quota: skip this call, don't crash the pipeline
    return {}
