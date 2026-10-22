"""Polite same-host crawler: robots.txt, sitemaps, page extraction."""
import json
import re
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from urllib import robotparser
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

from .models import Page
from .classify import classify

log = logging.getLogger("audit")

UA = "Mozilla/5.0 (compatible; TreatmentSEOAudit/0.1; SEO audit, contact via repo)"
SKIP_EXT = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".mp4", ".mp3", ".zip",
            ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".css", ".js", ".ico", ".woff", ".woff2",
            ".xml", ".json", ".txt")

PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[\s.\-]?)?\(?([2-9]\d{2})\)?[\s.\-]?(\d{3})[\s.\-]?(\d{4})(?!\d)")
ADDR_RE = re.compile(
    r"\b\d{1,6}\s+[A-Za-z0-9.'\- ]{2,40}?\s(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|"
    r"Lane|Ln|Way|Pike|Highway|Hwy|Parkway|Pkwy|Court|Ct|Place|Pl|Circle|Cir|Trail|Trl|Loop|Terrace|Ter)\b\.?"
    r"[,\s]+(?:(?:Suite|Ste|Unit|#)\s*[\w\-]+[,\s]+)?[A-Za-z .]{2,40}[,\s]+[A-Z]{2}\s+\d{5}",
    re.I)

MENTION_TERMS = {
    "joint_commission": [r"joint commission", r"\bjcaho\b"],
    "carf": [r"\bcarf\b"],
    "legitscript": [r"legitscript"],
    "naatp": [r"\bnaatp\b"],
    "state_license": [r"licensed by the state", r"state[- ]licensed", r"department of mental health"],
    "medically_reviewed": [r"medically reviewed", r"clinically reviewed", r"reviewed by"],
    "author_byline": [r"written by", r"\bby\s+[A-Z][a-z]+\s+[A-Z][a-z]+,?\s+(?:MD|LCSW|LPC|LADAC|PhD|PsyD|NP|RN|MSW)\b"],
    "credentials": [r"\b(?:MD|LCSW|LPC|LADAC|LADC|PhD|PsyD|NP|RN|MSW|CADC|LMFT|DO)\b"],
    "available_24_7": [r"24\s*/\s*7", r"24 hours", r"around the clock", r"day or night"],
    "insurance_payers": [r"aetna", r"cigna", r"blue ?cross", r"\bbcbs\b", r"united ?health", r"\buhc\b",
                         r"humana", r"anthem", r"optum", r"tricare", r"medicaid", r"medicare",
                         r"in[- ]network", r"out[- ]of[- ]network"],
    "verify_insurance": [r"verify (?:your )?(?:insurance|benefits|coverage)", r"insurance verification",
                         r"check (?:your )?(?:insurance|coverage|benefits)"],
    "hipaa": [r"\bhipaa\b"],
    "confidential": [r"confidential"],
    "same_day": [r"same[- ]day", r"immediate admission", r"admit today"],
}
MENTION_RE = {k: [re.compile(p, re.I) for p in v] for k, v in MENTION_TERMS.items()}

HEADER_CLASS_RE = re.compile(r"header|navbar|topbar|top-bar|masthead|site-nav|main-nav|utility", re.I)


def norm_host(host: str) -> str:
    host = (host or "").lower()
    return host[4:] if host.startswith("www.") else host


def is_asset(url: str) -> bool:
    path = urlparse(url).path.lower()
    return path.endswith(SKIP_EXT) or "/wp-content/" in path or "/wp-includes/" in path or "/wp-json/" in path


def normalize_url(url: str) -> str:
    url, _ = urldefrag(url)
    p = urlparse(url)
    path = p.path or "/"
    query = ""  # drop query strings: treatment sites rarely need them for indexable pages
    return f"{p.scheme}://{p.netloc}{path}{query}"


class Crawler:
    def __init__(self, start_url: str, max_pages: int = 150, workers: int = 6, delay: float = 0.2,
                 timeout: int = 20):
        self.start_url = start_url if start_url.startswith("http") else "https://" + start_url
        self.host = norm_host(urlparse(self.start_url).netloc)
        self.max_pages = max_pages
        self.workers = workers
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
        self.robots_txt = ""
        self.robots_status = 0
        self.robots = robotparser.RobotFileParser()
        self.sitemap_urls: list[str] = []
        self.sitemap_sources: list[str] = []
        self.sitemap_errors: list[str] = []
        self.pages: dict[str, Page] = {}
        self.home_final_url = ""
        self.llms_txt_status = 0

    # ---------- discovery ----------
    def fetch_robots(self):
        url = urljoin(self.start_url, "/robots.txt")
        try:
            r = self.session.get(url, timeout=self.timeout)
            self.robots_status = r.status_code
            if r.status_code == 200 and "text" in r.headers.get("Content-Type", "text"):
                self.robots_txt = r.text
                self.robots.parse(r.text.splitlines())
            else:
                self.robots.parse([])
        except requests.RequestException as e:
            log.warning("robots.txt fetch failed: %s", e)
            self.robots.parse([])
        try:
            r = self.session.get(urljoin(self.start_url, "/llms.txt"), timeout=self.timeout)
            self.llms_txt_status = r.status_code if "text/plain" in r.headers.get("Content-Type", "") else (404 if r.status_code == 200 else r.status_code)
        except requests.RequestException:
            self.llms_txt_status = 0

    def fetch_sitemaps(self):
        candidates = [m.split(":", 1)[1].strip() for m in self.robots_txt.splitlines()
                      if m.lower().startswith("sitemap:")]
        if not candidates:
            candidates = [urljoin(self.start_url, p) for p in ("/sitemap.xml", "/sitemap_index.xml", "/wp-sitemap.xml")]
        seen = set()
        queue = list(candidates)
        while queue and len(seen) < 50:
            sm = queue.pop(0)
            if sm in seen:
                continue
            seen.add(sm)
            try:
                r = self.session.get(sm, timeout=self.timeout)
            except requests.RequestException as e:
                self.sitemap_errors.append(f"{sm}: {e.__class__.__name__}")
                continue
            if r.status_code != 200:
                self.sitemap_errors.append(f"{sm}: HTTP {r.status_code}")
                continue
            try:
                soup = BeautifulSoup(r.content, "xml")
            except Exception:
                soup = BeautifulSoup(r.content, "lxml")
            self.sitemap_sources.append(sm)
            if soup.find("sitemapindex"):
                queue.extend(loc.get_text(strip=True) for loc in soup.find_all("loc"))
            else:
                for loc in soup.find_all("loc"):
                    u = loc.get_text(strip=True)
                    if norm_host(urlparse(u).netloc) == self.host and not is_asset(u):
                        self.sitemap_urls.append(normalize_url(u))
        self.sitemap_urls = list(dict.fromkeys(self.sitemap_urls))

    # ---------- fetching ----------
    def allowed(self, url: str) -> bool:
        try:
            return self.robots.can_fetch("*", url)
        except Exception:
            return True

    def fetch_page(self, url: str) -> Page:
        page = Page(url=url)
        if not self.allowed(url):
            page.error = "blocked by robots.txt"
            return page
        time.sleep(self.delay)
        t0 = time.time()
        try:
            r = self.session.get(url, timeout=self.timeout, allow_redirects=True)
        except requests.RequestException as e:
            page.error = e.__class__.__name__
            return page
        page.fetch_ms = int((time.time() - t0) * 1000)
        page.status = r.status_code
        page.redirects = len(r.history)
        page.final_url = normalize_url(r.url)
        page.content_type = r.headers.get("Content-Type", "")
        page.x_robots = r.headers.get("X-Robots-Tag", "")
        page.html_bytes = len(r.content)
        if page.is_html and r.status_code == 200:
            try:
                self.extract(page, r.text)
            except Exception as e:  # never let one page kill the crawl
                page.error = f"extract: {e.__class__.__name__}: {e}"
        page.page_type, page.intent_weight = classify(page.final_url or url, page.title)
        return page

    # ---------- extraction ----------
    def extract(self, page: Page, html: str):
        soup = BeautifulSoup(html, "lxml")
        base = page.final_url or page.url
        page.title = (soup.title.get_text(strip=True) if soup.title else "")
        md = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
        page.meta_description = (md.get("content") or "").strip() if md else ""
        mr = soup.find("meta", attrs={"name": re.compile("^robots$", re.I)})
        page.meta_robots = (mr.get("content") or "") if mr else ""
        can = soup.find("link", rel=lambda v: v and "canonical" in v)
        page.canonical = normalize_url(urljoin(base, can.get("href"))) if can and can.get("href") else ""
        page.h1s = [h.get_text(" ", strip=True) for h in soup.find_all("h1")]
        page.h2_count = len(soup.find_all("h2"))
        page.has_viewport = bool(soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)}))
        page.forms = len(soup.find_all("form"))
        page.scripts = len(soup.find_all("script", src=True))
        imgs = soup.find_all("img")
        page.images = len(imgs)
        page.images_no_alt = sum(1 for i in imgs if not (i.get("alt") or "").strip())
        page.mixed_content = sum(1 for t in soup.find_all(["img", "script", "iframe", "link"])
                                 if str(t.get("src") or t.get("href") or "").startswith("http://"))
        page.has_map = any("google.com/maps" in (f.get("src") or "") or "maps.google" in (f.get("src") or "")
                           for f in soup.find_all("iframe"))

        # JSON-LD
        for s in soup.find_all("script", type=re.compile("ld\\+json", re.I)):
            try:
                data = json.loads(s.string or s.get_text() or "{}")
            except json.JSONDecodeError:
                page.jsonld_types.append("INVALID_JSON")
                continue
            page.jsonld_raw.append(data)
            page.jsonld_types.extend(self._types(data))

        # tel links + header phone
        tel = [a.get("href") for a in soup.find_all("a", href=re.compile(r"^tel:", re.I))]
        page.tel_links = list(dict.fromkeys(re.sub(r"\D", "", t) for t in tel))
        header_zone = soup.find("header") or soup.find(attrs={"class": HEADER_CLASS_RE}) or soup.find(attrs={"id": HEADER_CLASS_RE})
        if header_zone and header_zone.find("a", href=re.compile(r"^tel:", re.I)):
            page.header_has_tel = True
        elif not header_zone and tel:
            # no identifiable header: treat a tel link in the first 20% of markup as "header"
            cut = html[: max(len(html) // 5, 4000)]
            page.header_has_tel = bool(re.search(r'href=["\']tel:', cut, re.I))

        # text
        for t in soup(["script", "style", "noscript", "template"]):
            t.decompose()
        text = soup.get_text(" ", strip=True)
        page.word_count = len(text.split())
        main = soup.find("main") or soup.find("article") or soup.find(attrs={"role": "main"})
        page.main_word_count = len(main.get_text(" ", strip=True).split()) if main else page.word_count
        page.phones_in_text = list(dict.fromkeys("".join(m) for m in PHONE_RE.findall(text)))[:10]
        page.addresses = list(dict.fromkeys(" ".join(a.split()) for a in ADDR_RE.findall(text)))[:5]
        page.mentions = {k: any(rx.search(text) for rx in v) for k, v in MENTION_RE.items()}

        heads = [h.get_text(" ", strip=True) for h in soup.find_all(["h2", "h3"])]
        page.question_headings = sum(1 for h in heads if h.strip().endswith("?"))
        page.has_faq = ("FAQPage" in page.jsonld_types) or page.question_headings >= 3 or len(soup.find_all("details")) >= 3

        # links
        internal, external = [], 0
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            u = urljoin(base, href)
            p = urlparse(u)
            if p.scheme not in ("http", "https"):
                continue
            if norm_host(p.netloc) == self.host:
                if not is_asset(u):
                    internal.append(normalize_url(u))
            else:
                external += 1
        page.internal_links = list(dict.fromkeys(internal))
        page.external_links = external

    @staticmethod
    def _types(data) -> list:
        out = []
        if isinstance(data, list):
            for d in data:
                out.extend(Crawler._types(d))
        elif isinstance(data, dict):
            t = data.get("@type")
            if isinstance(t, list):
                out.extend(str(x) for x in t)
            elif t:
                out.append(str(t))
            for k in ("@graph", "mainEntity", "itemListElement"):
                if k in data:
                    out.extend(Crawler._types(data[k]))
        return out

    # ---------- orchestration ----------
    def run(self) -> dict:
        log.info("robots.txt + sitemaps for %s", self.host)
        self.fetch_robots()
        self.fetch_sitemaps()
        start = normalize_url(self.start_url)
        seeds = [start] + [u for u in self.sitemap_urls if u != start]
        seen = set(seeds)
        queue = list(seeds)
        sitemap_set = set(self.sitemap_urls)
        log.info("sitemap urls: %d, crawling up to %d pages", len(self.sitemap_urls), self.max_pages)
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            while queue and len(self.pages) < self.max_pages:
                # crawl high-intent URLs first so the page cap never drops admissions/location pages
                queue.sort(key=lambda u: -classify(u)[1])
                batch = queue[: min(self.workers * 3, self.max_pages - len(self.pages))]
                queue = queue[len(batch):]
                for page in ex.map(self.fetch_page, batch):
                    page.in_sitemap = page.url in sitemap_set or page.final_url in sitemap_set
                    self.pages[page.url] = page
                    if page.url == start:
                        self.home_final_url = page.final_url
                    for link in page.internal_links:
                        if link not in seen and len(seen) < self.max_pages * 4:
                            seen.add(link)
                            queue.append(link)
                log.info("crawled %d pages, %d queued", len(self.pages), len(queue))
        return {
            "start_url": self.start_url,
            "host": self.host,
            "home_final_url": self.home_final_url,
            "robots_txt": self.robots_txt,
            "robots_status": self.robots_status,
            "llms_txt_status": self.llms_txt_status,
            "sitemap_sources": self.sitemap_sources,
            "sitemap_urls": self.sitemap_urls,
            "sitemap_errors": self.sitemap_errors,
            "pages": self.pages,
            "uncrawled": len(queue),
        }
