"""Stage 1: Discovery. Search YouTube for channels per niche query, then pull channel details."""
from datetime import datetime, timezone
import config, youtube

def search_channel_ids(query, pages=1, region=None):
    ids, token = [], None
    for _ in range(pages):
        params = {"part": "snippet", "type": "channel", "q": query, "maxResults": 50}
        if region: params["regionCode"] = region
        if token: params["pageToken"] = token
        data = youtube.get("search", params)
        ids += [it["snippet"]["channelId"] for it in data.get("items", []) if it.get("snippet")]
        token = data.get("nextPageToken")
        if not token: break
    return ids

def fetch_channels(ids):
    out = []
    for i in range(0, len(ids), 50):
        data = youtube.get("channels", {
            "part": "snippet,statistics,contentDetails", "id": ",".join(ids[i:i+50]), "maxResults": 50})
        out += data.get("items", [])
    return out

def discover(conn, queries=None, pages=None):
    queries = queries or config.DISCOVERY_QUERIES
    pages = pages or config.PAGES_PER_QUERY
    new = 0
    for q in queries:
        found = search_channel_ids(q, pages, config.SEARCH_REGION)
        found = [c for c in dict.fromkeys(found)
                 if not conn.execute("SELECT 1 FROM influencers WHERE channel_id=?", (c,)).fetchone()]
        for ch in fetch_channels(found):
            sn, st = ch.get("snippet", {}), ch.get("statistics", {})
            followers = None if st.get("hiddenSubscriberCount") else _int(st.get("subscriberCount"))
            conn.execute(
                "INSERT OR IGNORE INTO influencers(channel_id,name,platform,profile_url,followers,country,"
                "description,discovered_via,discovered_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (ch["id"], sn.get("title"), "YouTube", f"https://www.youtube.com/channel/{ch['id']}",
                 followers, sn.get("country"), sn.get("description", ""), q,
                 datetime.now(timezone.utc).isoformat()))
            new += 1
        conn.commit()
        print(f"[discover] '{q}': {len(found)} new channels")
    return new

def _int(x):
    try: return int(x)
    except (TypeError, ValueError): return None
