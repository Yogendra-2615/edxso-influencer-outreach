"""SQLite storage: influencers, messages, outreach_log."""
import sqlite3
import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS influencers(
  channel_id TEXT PRIMARY KEY, name TEXT, platform TEXT, profile_url TEXT,
  followers INTEGER, engagement_rate REAL, niche TEXT, content_themes TEXT,
  email TEXT, email_source TEXT, instagram TEXT, website TEXT, country TEXT,
  description TEXT, recent_videos TEXT, last_upload TEXT, relevance_score INTEGER,
  status TEXT DEFAULT 'discovered', filter_reasons TEXT, enriched INTEGER DEFAULT 0,
  discovered_via TEXT, discovered_at TEXT);
CREATE TABLE IF NOT EXISTS messages(
  channel_id TEXT PRIMARY KEY, email_subject TEXT, email_body TEXT, instagram_dm TEXT,
  model TEXT, valid INTEGER, notes TEXT, generated_at TEXT);
CREATE TABLE IF NOT EXISTS outreach_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, channel_id TEXT, email TEXT, medium TEXT,
  status TEXT, error TEXT, sent_at TEXT);
-- Hard guarantee against duplicate real sends, even if code logic is bypassed.
CREATE UNIQUE INDEX IF NOT EXISTS ux_real_send ON outreach_log(email, medium) WHERE status='sent';
"""

def connect(path=None):
    conn = sqlite3.connect(path or config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn
