"""Stage 4: AI personalization. One LLM call per influencer -> email (60-90 words) + Instagram DM (15-30 words).
Messages are validated against the word limits and regenerated with feedback if out of range."""
import json, re
from datetime import datetime, timezone
import config

EMAIL_RANGE, DM_RANGE = (60, 90), (15, 30)

SYSTEM = (
    "You write short, warm, human-sounding brand-collaboration outreach to micro-influencers. "
    "Use ONLY the facts provided. Never invent content, products, results, numbers or compliments about "
    "things not listed. Reference one of the provided recent video titles naturally, not as a quote dump. "
    "No emojis in the email, at most one in the DM. No buzzwords like 'synergy'. Return ONLY valid JSON."
)

def word_count(text):
    return len(re.findall(r"[\w'’\-]+", text or ""))

def pick_angle(followers, er):
    """Rule-based collaboration angle so the offer fits the creator's size, not one fixed template."""
    if followers < 15_000:   return "barter collaboration (free product seeding in exchange for honest content)"
    if followers < 40_000:   return "UGC content creation (paid) plus an affiliate code"
    if er and er >= 6:       return "brand ambassador program (long-term, high-engagement audience)"
    return "paid sponsorship of one dedicated video"

def build_prompt(rec, feedback=""):
    first = (rec["name"] or "there").split()[0]
    return f"""Creator facts:
- Name: {rec['name']} (greeting name: {first})
- Platform: {rec['platform']}, {rec['followers']:,} followers, {rec['engagement_rate']}% engagement
- Niche: {rec['niche']}; content themes: {rec['content_themes']}
- Recent video titles: {rec['recent_videos']}
- Channel description (tone/style clues): {(rec['description'] or '')[:400]}
- Audience country (if known): {rec['country'] or 'unknown'}

Brand: {config.BRAND_NAME}, offering: {config.BRAND_PRODUCT}
Proposed collaboration: {pick_angle(rec['followers'], rec['engagement_rate'])}
Sender: {config.SENDER_NAME}, {config.SENDER_TITLE}

Write:
1. email_subject (max 8 words)
2. email_body: {EMAIL_RANGE[0]}-{EMAIL_RANGE[1]} words INCLUDING greeting and sign-off. Reference their niche, a recent video, the audience fit, the collaboration and the value to them.
3. instagram_dm: {DM_RANGE[0]}-{DM_RANGE[1]} words, casual, personalized, one clear ask.
{feedback}
JSON keys exactly: email_subject, email_body, instagram_dm."""

def _parse(raw):
    m = re.search(r"\{.*\}", raw, re.S)
    return json.loads(m.group(0))

def validate(msg):
    problems = []
    e, d = word_count(msg.get("email_body")), word_count(msg.get("instagram_dm"))
    if not EMAIL_RANGE[0] <= e <= EMAIL_RANGE[1]: problems.append(f"email_body was {e} words; must be {EMAIL_RANGE[0]}-{EMAIL_RANGE[1]}")
    if not DM_RANGE[0] <= d <= DM_RANGE[1]: problems.append(f"instagram_dm was {d} words; must be {DM_RANGE[0]}-{DM_RANGE[1]}")
    if not msg.get("email_subject"): problems.append("missing email_subject")
    return problems

def generate(rec, llm, max_tries=3):
    """llm: callable(system, prompt) -> str. Returns (message_dict, problems_left)."""
    feedback, msg, problems = "", {}, ["not generated"]
    for _ in range(max_tries):
        try:
            msg = _parse(llm(SYSTEM, build_prompt(rec, feedback)))
            problems = validate(msg)
        except Exception as e:
            problems = [f"bad output: {e}"]
        if not problems: break
        feedback = "Previous attempt failed: " + "; ".join(problems) + ". Fix and return JSON again."
    return msg, problems

def anthropic_llm():
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    def call(system, prompt):
        r = client.messages.create(model=config.LLM_MODEL, max_tokens=800, system=system,
                                   messages=[{"role": "user", "content": prompt}])
        return r.content[0].text
    return call

def personalize_all(conn, llm=None):
    llm = llm or anthropic_llm()
    rows = conn.execute("""SELECT i.* FROM influencers i LEFT JOIN messages m ON m.channel_id=i.channel_id
                           WHERE i.status='passed' AND m.channel_id IS NULL""").fetchall()
    for r in rows:
        msg, problems = generate(dict(r), llm)
        conn.execute("INSERT OR REPLACE INTO messages VALUES(?,?,?,?,?,?,?,?)", (
            r["channel_id"], msg.get("email_subject"), msg.get("email_body"), msg.get("instagram_dm"),
            config.LLM_MODEL, 0 if problems else 1, "; ".join(problems),
            datetime.now(timezone.utc).isoformat()))
        conn.commit()
        print(f"[personalize] {r['name']}: {'OK' if not problems else 'NEEDS REVIEW - ' + '; '.join(problems)}")
