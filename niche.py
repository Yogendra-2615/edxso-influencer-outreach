"""Fashion & Beauty vocabulary used for relevance scoring and content-theme extraction."""
import re

THEMES = {
    "skincare": ["skincare", "skin care", "serum", "moisturizer", "moisturiser", "sunscreen", "spf", "acne", "cleanser", "glass skin"],
    "makeup": ["makeup", "make-up", "foundation", "lipstick", "eyeshadow", "mascara", "grwm", "get ready with me", "blush", "concealer", "eyeliner"],
    "haircare": ["haircare", "hair care", "hairstyle", "curls", "shampoo", "hair routine", "hair mask"],
    "fragrance & nails": ["fragrance", "perfume", "nail art", "manicure", "nails"],
    "outfits & styling": ["outfit", "outfits", "ootd", "lookbook", "styling", "wardrobe", "capsule wardrobe", "haul", "fashion"],
    "thrift & sustainable fashion": ["thrift", "thrifting", "thrifted", "sustainable fashion", "secondhand", "upcycle"],
    "ethnic & festive wear": ["saree", "sari", "lehenga", "kurti", "ethnic wear", "indo-western"],
    "accessories": ["jewellery", "jewelry", "handbag", "sneakers", "accessories"],
}
BEAUTY = {"skincare", "makeup", "haircare", "fragrance & nails"}
FASHION = set(THEMES) - BEAUTY

def _hits(text, kws):
    return {k for k in kws if re.search(r"(?<!\w)" + re.escape(k) + r"(?!\w)", text)}

def analyse(text):
    """Return (distinct_keyword_count, ordered_theme_list, niche_label)."""
    text = (text or "").lower()
    per_theme = {t: _hits(text, kws) for t, kws in THEMES.items()}
    total = sum(len(h) for h in per_theme.values())
    themes = [t for t, h in sorted(per_theme.items(), key=lambda x: -len(x[1])) if h]
    b = sum(len(per_theme[t]) for t in BEAUTY)
    f = sum(len(per_theme[t]) for t in FASHION)
    if b >= 2 and f >= 2: niche = "Fashion & Beauty"
    elif b >= 2 and b > f: niche = "Beauty"
    elif f >= 2 and f > b: niche = "Fashion"
    else: niche = "Unclear / Other"
    return total, themes, niche
