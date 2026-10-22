"""Classify pages by how close they are to a phone call or admission."""
import re
from urllib.parse import urlparse

CONVERSION = ["admission", "insurance", "verify", "cost", "pricing", "payment", "pay-for",
              "contact", "get-help", "get-started", "what-to-expect", "financ", "tour",
              "call-us", "intake", "assessment"]
LOCAL = ["location", "locations", "/centers/", "/center-", "near-me", "outpatient-center",
         "campus", "facility", "facilities"]
PROGRAM = ["treatment", "program", "rehab", "detox", "residential", "inpatient", "outpatient",
           "/iop", "/php", "alcohol", "drug", "opioid", "heroin", "cocaine", "meth", "benzo",
           "fentanyl", "mental-health", "dual-diagnosis", "co-occurring", "therapy", "recovery",
           "sober", "adolescent", "teen", "young-adult", "women", "men", "veteran", "professional",
           "family", "aftercare", "services", "levels-of-care", "clinical"]
CONTENT = ["blog", "news", "article", "resources", "event", "podcast", "story", "stories",
           "press", "/20", "webinar", "video"]
ABOUT = ["about", "staff", "team", "leadership", "career", "job", "donate", "foundation",
         "alumni", "accredit", "faq", "privacy", "terms", "mission", "history", "board"]

WEIGHTS = {"archive": 1, "home": 5, "conversion": 5, "local": 4, "program": 4, "about": 2, "content": 1, "other": 2}


def classify(url: str, title: str = "") -> tuple[str, int]:
    path = urlparse(url).path.rstrip("/").lower()
    if path in ("", "/", "/index.html", "/index.php", "/home"):
        return "home", WEIGHTS["home"]
    if re.search(r"^/(tag|category|author|member-category|page)/|/page/\d+|/feed/?$|/attachment/", path):
        return "archive", WEIGHTS["archive"]
    s = path + " " + (title or "").lower()
    for name, keys in (("conversion", CONVERSION), ("local", LOCAL), ("content", CONTENT),
                       ("program", PROGRAM), ("about", ABOUT)):
        if any(k in s for k in keys):
            return name, WEIGHTS[name]
    return "other", WEIGHTS["other"]
