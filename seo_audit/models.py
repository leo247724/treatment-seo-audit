from dataclasses import dataclass, field, asdict
from typing import Optional
import math
import re


@dataclass
class Page:
    url: str
    final_url: str = ""
    status: int = 0
    redirects: int = 0
    content_type: str = ""
    fetch_ms: int = 0
    html_bytes: int = 0
    title: str = ""
    meta_description: str = ""
    meta_robots: str = ""
    x_robots: str = ""
    canonical: str = ""
    h1s: list = field(default_factory=list)
    h2_count: int = 0
    word_count: int = 0
    main_word_count: int = 0
    has_viewport: bool = False
    jsonld_types: list = field(default_factory=list)
    jsonld_raw: list = field(default_factory=list)
    tel_links: list = field(default_factory=list)
    header_has_tel: bool = False
    phones_in_text: list = field(default_factory=list)
    addresses: list = field(default_factory=list)
    has_map: bool = False
    forms: int = 0
    has_faq: bool = False
    question_headings: int = 0
    mentions: dict = field(default_factory=dict)
    internal_links: list = field(default_factory=list)
    external_links: int = 0
    images: int = 0
    images_no_alt: int = 0
    scripts: int = 0
    mixed_content: int = 0
    page_type: str = "other"
    intent_weight: int = 2
    in_sitemap: bool = False
    error: str = ""

    @property
    def is_html(self) -> bool:
        ct = (self.content_type or "").lower()
        return "text/html" in ct or "application/xhtml+xml" in ct

    @property
    def noindex(self) -> bool:
        s = (self.meta_robots + " " + self.x_robots).lower()
        return "noindex" in s or "none" in re.split(r"[\s,:]+", s)  # "none" == noindex, nofollow

    @property
    def indexable(self) -> bool:
        return self.status == 200 and self.is_html and not self.noindex

    def to_dict(self):
        d = asdict(self)
        d.pop("jsonld_raw", None)
        d["indexable"] = self.indexable
        return d


@dataclass
class Finding:
    id: str
    category: str          # conversion | local | trust | technical | ai_visibility | content
    title: str
    severity: int          # 1 (cosmetic) .. 5 (blocks inquiries)
    intent_weight: int     # 1 .. 5, how close affected pages are to a call/admission
    pages: list            # example affected URLs
    page_count: int
    evidence: list
    why_it_matters: str
    fix: str
    check_first: str       # what to look at in GSC / call tracking before acting
    confidence: str = "medium"  # high | medium | low  (how sure the automated check is)
    impact: float = 0.0

    def score(self) -> float:
        reach = 1 + min(math.log10(max(self.page_count, 1)), 1.0)
        self.impact = round(self.severity * self.intent_weight * reach, 1)
        return self.impact

    def to_dict(self):
        return asdict(self)
