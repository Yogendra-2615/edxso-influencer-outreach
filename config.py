"""Central configuration. Everything tunable lives here or in .env."""
import os
from dotenv import load_dotenv

load_dotenv()

def _csv(name, default=""):
    return [x.strip().upper() for x in os.getenv(name, default).split(",") if x.strip()]

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
DB_PATH = os.getenv("DB_PATH", "outreach.db")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

# Brand / sender
BRAND_NAME = os.getenv("BRAND_NAME", "YourBrand")
BRAND_PRODUCT = os.getenv("BRAND_PRODUCT", "skincare range")
SENDER_NAME = os.getenv("SENDER_NAME", "Your Name")
SENDER_TITLE = os.getenv("SENDER_TITLE", "Partnerships")

# Sending
DRY_RUN = os.getenv("DRY_RUN", "true").lower() != "false"
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SEND_DELAY_SECONDS = float(os.getenv("SEND_DELAY_SECONDS", "2"))

# Discovery
DISCOVERY_QUERIES = [
    "skincare routine", "makeup tutorial", "get ready with me", "outfit ideas",
    "thrift haul fashion", "hair care routine", "korean skincare review",
    "affordable fashion lookbook", "grwm makeup", "capsule wardrobe styling",
    "drugstore makeup review", "ootd styling tips",
]
PAGES_PER_QUERY = int(os.getenv("PAGES_PER_QUERY", "2"))      # 50 results/page
SEARCH_REGION = os.getenv("SEARCH_REGION", "") or None          # e.g. IN, US
RECENT_VIDEOS = 10

# Filtering (Fashion & Beauty category)
ALLOWED_PLATFORMS = {"YouTube"}
MIN_FOLLOWERS = int(os.getenv("MIN_FOLLOWERS", "5000"))
MAX_FOLLOWERS = int(os.getenv("MAX_FOLLOWERS", "100000"))
MIN_ENGAGEMENT = float(os.getenv("MIN_ENGAGEMENT", "2.0"))     # percent
MIN_RELEVANCE = int(os.getenv("MIN_RELEVANCE", "4"))           # distinct niche keywords
MAX_DAYS_SINCE_UPLOAD = int(os.getenv("MAX_DAYS_SINCE_UPLOAD", "90"))
TARGET_COUNTRIES = _csv("TARGET_COUNTRIES")                    # empty = any
BLOCKED_TERMS = ["gambling", "casino", "betting", "nsfw", "adult only", "forex", "crypto signals"]
