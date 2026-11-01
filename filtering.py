"""Stage 3: Filtering & classification (Fashion & Beauty). Every check is recorded as PASS/FAIL with a reason."""
import re
from datetime import datetime, timezone, timedelta
import config

def evaluate(r):
    """r: dict-like influencer record. Returns (passed: bool, reasons: list[str])."""
    checks = []
    def chk(ok, msg): checks.append((bool(ok), msg))

    chk(r["platform"] in config.ALLOWED_PLATFORMS, f"platform {r['platform']}")
    f = r["followers"]
    chk(f is not None and config.MIN_FOLLOWERS <= f <= config.MAX_FOLLOWERS,
        f"followers {f if f is not None else 'hidden/unknown'} (need {config.MIN_FOLLOWERS:,}-{config.MAX_FOLLOWERS:,})")
    er = r["engagement_rate"]
    chk(er is not None and er >= config.MIN_ENGAGEMENT,
        f"engagement {er if er is not None else 'unavailable'}% (need >= {config.MIN_ENGAGEMENT}%)")
    chk(r["niche"] in ("Fashion", "Beauty", "Fashion & Beauty") and (r["relevance_score"] or 0) >= config.MIN_RELEVANCE,
        f"niche '{r['niche']}', relevance {r['relevance_score']} (need >= {config.MIN_RELEVANCE} niche keywords)")
    if r["last_upload"]:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(r["last_upload"].replace("Z", "+00:00"))
        chk(age <= timedelta(days=config.MAX_DAYS_SINCE_UPLOAD), f"last upload {age.days} days ago (need <= {config.MAX_DAYS_SINCE_UPLOAD})")
    else:
        chk(False, "no recent uploads found")
    blob = " ".join([(r["description"] or ""), (r["recent_videos"] or "")]).lower()
    hit = [t for t in config.BLOCKED_TERMS if re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", blob)]
    chk(not hit, "brand-safety: " + (f"blocked terms {hit}" if hit else "no blocked terms"))
    if config.TARGET_COUNTRIES and r["country"]:
        chk(r["country"].upper() in config.TARGET_COUNTRIES, f"country {r['country']} (target {config.TARGET_COUNTRIES})")
    elif config.TARGET_COUNTRIES:
        checks.append((True, "country unknown (not penalised)"))

    reasons = [("PASS: " if ok else "FAIL: ") + m for ok, m in checks]
    return all(ok for ok, _ in checks), reasons

def filter_all(conn):
    rows = conn.execute("SELECT * FROM influencers WHERE enriched=1").fetchall()
    p = 0
    for r in rows:
        ok, reasons = evaluate(dict(r))
        conn.execute("UPDATE influencers SET status=?, filter_reasons=? WHERE channel_id=?",
                     ("passed" if ok else "failed", " | ".join(reasons), r["channel_id"]))
        p += ok
    conn.commit()
    print(f"[filter] {p} passed, {len(rows) - p} failed of {len(rows)}")
