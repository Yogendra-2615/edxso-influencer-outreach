"""Stage 6: Export dataset, messages and outreach tracker to CSV + one Excel workbook."""
import csv, os
import config

QUERIES = {
 "influencer_dataset": """SELECT name AS Name, platform AS Platform, followers AS Followers,
    engagement_rate AS 'Engagement %', niche AS Niche, email AS Email, profile_url AS 'Profile URL',
    content_themes AS 'Content Theme', instagram AS Instagram, website AS Website, country AS Country,
    status AS Status, filter_reasons AS 'Filter Reasons' FROM influencers ORDER BY status, followers DESC""",
 "personalized_messages": """SELECT i.name AS Influencer, i.email AS Email, m.email_subject AS Subject,
    m.email_body AS 'Email Pitch', m.instagram_dm AS 'Instagram DM', m.valid AS 'Validated', m.notes AS Notes
    FROM messages m JOIN influencers i ON i.channel_id=m.channel_id""",
 "outreach_tracker": """SELECT i.name AS Influencer, o.email AS Email, o.medium AS Medium,
    CASE WHEN m.channel_id IS NOT NULL THEN 'Yes' ELSE 'No' END AS 'Message Generated',
    o.sent_at AS 'Sent Date', o.status AS Status, o.error AS Error
    FROM outreach_log o JOIN influencers i ON i.channel_id=o.channel_id
    LEFT JOIN messages m ON m.channel_id=o.channel_id ORDER BY o.id""",
}

def export_all(conn):
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    from openpyxl import Workbook
    wb = Workbook(); wb.remove(wb.active)
    for name, q in QUERIES.items():
        cur = conn.execute(q); cols = [c[0] for c in cur.description]; rows = cur.fetchall()
        with open(os.path.join(config.OUTPUT_DIR, name + ".csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(cols); w.writerows(rows)
        ws = wb.create_sheet(name[:31]); ws.append(cols)
        for r in rows: ws.append(list(r))
    wb.save(os.path.join(config.OUTPUT_DIR, "outreach_report.xlsx"))
    print(f"[export] files written to ./{config.OUTPUT_DIR}/")
