"""Tests use small SYNTHETIC records defined inline. They exist only to test logic and are never exported as data."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
import config, db, enrichment, filtering, personalize, sender
from datetime import datetime, timezone, timedelta

def rec(**kw):
    base = dict(platform="YouTube", followers=20000, engagement_rate=4.0, niche="Beauty", relevance_score=6,
                last_upload=(datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
                description="skincare and makeup", recent_videos="a | b", country=None,
                name="Test Creator", content_themes="skincare; makeup")
    return {**base, **kw}

def test_email_extraction_never_guesses():
    assert enrichment.extract_email("business: hi@creator.com") == "hi@creator.com"
    assert enrichment.extract_email("no contact here") is None
    assert enrichment.extract_email("logo@2x.png") is None

def test_engagement_skips_hidden_likes():
    vids = [dict(likes=10, comments=0, views=100), dict(likes=None, comments=0, views=500)]
    assert enrichment.engagement_rate(vids) == 10.0
    assert enrichment.engagement_rate([]) is None

@pytest.mark.parametrize("kw,ok", [({}, True), ({"followers": 500}, False), ({"followers": 900000}, False),
    ({"engagement_rate": 0.4}, False), ({"engagement_rate": None}, False), ({"niche": "Unclear / Other"}, False),
    ({"followers": None}, False), ({"description": "casino betting tips"}, False)])
def test_filter(kw, ok):
    passed, reasons = filtering.evaluate(rec(**kw))
    assert passed is ok and reasons

def good_llm(system, prompt):
    return json.dumps({"email_subject": "Collab idea",
        "email_body": " ".join(["word"] * 70), "instagram_dm": " ".join(["dm"] * 20)})

def test_generate_ok_and_retry():
    msg, problems = personalize.generate(rec(), good_llm)
    assert problems == []
    calls = []
    def flaky(s, p):
        calls.append(p)
        return json.dumps({"email_subject": "x", "email_body": "too short", "instagram_dm": "short"}) if len(calls) == 1 else good_llm(s, p)
    _, problems = personalize.generate(rec(), flaky)
    assert problems == [] and "Previous attempt failed" in calls[1]

def test_dedupe_and_validity(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DRY_RUN", True)
    conn = db.connect(str(tmp_path / "t.db"))
    for cid, email in [("c1", "a@b.com"), ("c2", "Not Found"), ("c3", "a@b.com")]:
        conn.execute("INSERT INTO influencers(channel_id,name,platform,email,status) VALUES(?,?,?,?,?)", (cid, cid, "YouTube", email, "passed"))
        conn.execute("INSERT INTO messages VALUES(?,?,?,?,?,?,?,?)", (cid, "s", "b", "d", "m", 1, "", "now"))
    conn.commit()
    sender.send_emails(conn, sleep=lambda s: None)
    sender.send_emails(conn, sleep=lambda s: None)      # second run must not re-send
    rows = conn.execute("SELECT email FROM outreach_log WHERE medium='email'").fetchall()
    assert len(rows) == 1 and rows[0]["email"] == "a@b.com"   # c2 invalid, c3 duplicate address
