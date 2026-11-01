"""Stage 5: Sending layer. Email via SMTP (or simulated), Instagram DM via a manual queue (no platform bypass)."""
import re, smtplib, time
from datetime import datetime, timezone
from email.message import EmailMessage
import config

VALID_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
FOOTER = "\n\n--\nNot interested? Reply 'no thanks' and I won't contact you again."

def eligible(conn, real):
    """Passed influencers with a valid email, a validated message, and no prior outreach."""
    blocked = "('sent')" if real else "('sent','simulated')"
    rows = conn.execute(f"""
        SELECT i.channel_id, i.name, i.email, m.email_subject, m.email_body
        FROM influencers i JOIN messages m ON m.channel_id=i.channel_id
        WHERE i.status='passed' AND m.valid=1
          AND NOT EXISTS (SELECT 1 FROM outreach_log o
                          WHERE lower(o.email)=lower(i.email) AND o.medium='email' AND o.status IN {blocked})""").fetchall()
    seen, out = set(), []                       # also dedupe within this batch (same address on two profiles)
    for r in rows:
        key = (r["email"] or "").lower()
        if r["email"] and VALID_EMAIL.match(r["email"]) and key not in seen:
            seen.add(key); out.append(r)
    return out

def _log(conn, cid, email, medium, status, error=""):
    conn.execute("INSERT INTO outreach_log(channel_id,email,medium,status,error,sent_at) VALUES(?,?,?,?,?,?)",
                 (cid, email, medium, status, error, datetime.now(timezone.utc).isoformat()))
    conn.commit()

def _smtp_send(to, subject, body):
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = config.SMTP_USER, to, subject
    msg.set_content(body + FOOTER)
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as s:
        s.starttls(); s.login(config.SMTP_USER, config.SMTP_PASSWORD); s.send_message(msg)

def send_emails(conn, sleep=time.sleep):
    real = not config.DRY_RUN
    if real and not (config.SMTP_USER and config.SMTP_PASSWORD):
        raise RuntimeError("DRY_RUN=false needs SMTP_USER and SMTP_PASSWORD")
    todo = eligible(conn, real)
    for r in todo:
        if not real:
            _log(conn, r["channel_id"], r["email"], "email", "simulated")
            print(f"[send] SIMULATED -> {r['email']}")
            continue
        try:
            _smtp_send(r["email"], r["email_subject"], r["email_body"])
            _log(conn, r["channel_id"], r["email"], "email", "sent")
            print(f"[send] sent -> {r['email']}")
        except Exception as e:
            _log(conn, r["channel_id"], r["email"], "email", "failed", str(e))
            print(f"[send] FAILED -> {r['email']}: {e}")
        sleep(config.SEND_DELAY_SECONDS)
    print(f"[send] processed {len(todo)} emails ({'REAL' if real else 'DRY RUN'})")

def queue_dms(conn):
    """Instagram DMs are never auto-sent: they are queued for a human to send from the app."""
    rows = conn.execute("""SELECT i.channel_id, i.instagram, m.instagram_dm FROM influencers i
        JOIN messages m ON m.channel_id=i.channel_id
        WHERE i.status='passed' AND m.valid=1 AND i.instagram IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM outreach_log o WHERE o.channel_id=i.channel_id AND o.medium='instagram_dm')""").fetchall()
    for r in rows:
        _log(conn, r["channel_id"], "@" + r["instagram"], "instagram_dm", "pending_manual")
    print(f"[send] {len(rows)} Instagram DMs queued for manual sending")
