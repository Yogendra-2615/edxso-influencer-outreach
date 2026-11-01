"""Stage 2: Enrichment. Recent videos -> engagement rate, themes, niche, email/IG/website extraction."""
import re
from statistics import mean
import config, youtube, niche

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
IG_RE = re.compile(r"instagram\.com/([A-Za-z0-9_.]{2,30})", re.I)
URL_RE = re.compile(r"https?://[^\s)>\]]+", re.I)
SOCIAL = ("youtube.", "youtu.be", "instagram.", "facebook.", "twitter.", "x.com", "tiktok.", "t.me", "wa.me", "bit.ly", "amzn.", "linktr.ee")
BAD_EMAIL_SUFFIX = (".png", ".jpg", ".jpeg", ".gif", ".webp")
IG_RESERVED = {"p", "reel", "reels", "explore", "stories", "accounts"}

def extract_email(text):
    """First syntactically valid email found in public text, else None. Never guesses."""
    for m in EMAIL_RE.findall(text or ""):
        if m.lower().endswith(BAD_EMAIL_SUFFIX) or m.lower().startswith("example@"):
            continue
        return m.strip(".")
    return None

def extract_instagram(text):
    for h in IG_RE.findall(text or ""):
        if h.lower() not in IG_RESERVED:
            return h.rstrip(".")
    return None

def extract_website(text):
    for u in URL_RE.findall(text or ""):
        if not any(s in u.lower() for s in SOCIAL):
            return u.rstrip(".,")
    return None

def engagement_rate(videos):
    """Mean (likes+comments)/views over recent videos, in %. Skips videos with hidden likes or 0 views."""
    rates = [(v["likes"] + v["comments"]) / v["views"]
             for v in videos if v.get("likes") is not None and v.get("views")]
    return round(100 * mean(rates), 2) if rates else None

def _n(x):
    try: return int(x)
    except (TypeError, ValueError): return None

def fetch_recent_videos(channel_id, n=None):
    n = n or config.RECENT_VIDEOS
    uploads = "UU" + channel_id[2:]                    # uploads playlist convention
    pl = youtube.get("playlistItems", {"part": "contentDetails", "playlistId": uploads, "maxResults": n})
    ids = [i["contentDetails"]["videoId"] for i in pl.get("items", [])]
    if not ids: return []
    data = youtube.get("videos", {"part": "snippet,statistics", "id": ",".join(ids)})
    vids = []
    for it in data.get("items", []):
        st, sn = it.get("statistics", {}), it.get("snippet", {})
        vids.append({"title": sn.get("title", ""), "published": sn.get("publishedAt"),
                     "tags": sn.get("tags", []), "views": _n(st.get("viewCount")),
                     "likes": _n(st.get("likeCount")), "comments": _n(st.get("commentCount")) or 0})
    return sorted(vids, key=lambda v: v["published"] or "", reverse=True)

def enrich_record(rec, videos):
    """Pure function: builds the enrichment fields from a record + its recent videos."""
    corpus = " ".join([rec.get("description") or ""] + [v["title"] + " " + " ".join(v["tags"]) for v in videos])
    score, themes, label = niche.analyse(corpus)
    email = extract_email(rec.get("description"))
    return {
        "engagement_rate": engagement_rate(videos),
        "niche": label, "content_themes": "; ".join(themes[:4]) or "Not Found",
        "relevance_score": score,
        "email": email or "Not Found", "email_source": "channel description" if email else None,
        "instagram": extract_instagram(rec.get("description")),
        "website": extract_website(rec.get("description")),
        "last_upload": videos[0]["published"] if videos else None,
        "recent_videos": " | ".join(v["title"] for v in videos[:3]),
    }

def enrich_all(conn):
    rows = conn.execute("SELECT * FROM influencers WHERE enriched=0").fetchall()
    for r in rows:
        try:
            f = enrich_record(dict(r), fetch_recent_videos(r["channel_id"]))
        except youtube.QuotaExceeded:
            raise
        except Exception as e:                           # one bad profile must not stop the batch
            print(f"[enrich] {r['name']}: skipped ({e})")
            continue
        sets = ",".join(f"{k}=?" for k in f)
        conn.execute(f"UPDATE influencers SET {sets}, enriched=1 WHERE channel_id=?", (*f.values(), r["channel_id"]))
        conn.commit()
    print(f"[enrich] enriched {len(rows)} profiles")
