"""Competitor page comparison: what the pages winning the Nashville rehab SERPs do that the audited site does not.

Also scores each page's entity signals (0-100) and extracts its on-page strategy (internal links, nav, CTAs,
proof, outline) so the report can say what each competitor does and what the audited site should copy first."""
import json, os, re, time
from urllib.parse import urlparse, urljoin
from .models import Finding

BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
FALLBACK_COMPETITORS = [
    "https://apex.rehab/tennessee/nashville/", "https://www.recoveryunplugged.com/location/drug-rehab-in-nashville/",
    "https://southeastaddictiontn.com/", "https://www.liveagaindetox.com/", "https://www.recoveryranch.com/",
    "https://thenextdoorrecovery.org/"]
PREFERRED_PATHS = ["/", "/treatment/residential-care/", "/treatment/drug-and-alcohol-detox/",
                   "/admissions/insurance-and-finances/"]
SERVICE_RE = re.compile(r"\b(rehab|detox|addiction|treatment|recovery|substance|alcohol|drug|residential|"
                        r"outpatient|iop|php|inpatient)\b", re.I)
GEO_RE = re.compile(r"\b(nashville|tennessee|tn)\b", re.I)
INSURERS = {"aetna": r"\baetna\b", "bcbs": r"\bbcbs\b|blue\s*cross", "cigna": r"\bcigna\b",
            "unitedhealthcare": r"united\s*health\s*care|\buhc\b|\boptum\b", "humana": r"\bhumana\b",
            "tricare": r"\btricare\b"}
INSURERS_EXT = {**INSURERS, "anthem": r"\banthem\b", "ambetter": r"\bambetter\b", "magellan": r"\bmagellan\b",
                "beacon": r"\bbeacon\s+health", "carelon": r"\bcarelon\b", "multiplan": r"\bmultiplan\b",
                "tenncare": r"\btenncare\b", "amerigroup": r"\bamerigroup\b", "wellcare": r"\bwellcare\b",
                "compsych": r"\bcompsych\b", "geha": r"\bgeha\b", "first_health": r"\bfirst\s+health\b",
                "evernorth": r"\bevernorth\b", "meritain": r"\bmeritain\b", "umr": r"\bumr\b"}
ACCRED = {"joint_commission": r"joint\s+commission", "carf": r"\bcarf\b", "legitscript": r"legitscript"}
REVIEW_RE = re.compile(r"testimonial|review|stars?\b|rated\s+\d|\d\.\d\s*(out of|/)\s*5", re.I)

# --- entity score + on-page strategy ---------------------------------------------------------------
CITY = "nashville"
ENTITY_SIGNALS = [  # (key, points, label) -- sums to 100
    ("org_schema", 10, "Organization or MedicalOrganization JSON-LD"),
    ("local_schema", 10, "LocalBusiness/MedicalClinic/MedicalBusiness/Hospital JSON-LD type"),
    ("schema_telephone", 5, "schema telephone"),
    ("schema_address", 5, "schema address / PostalAddress"),
    ("schema_geo", 5, "schema geo"),
    ("schema_opening_hours", 5, "schema openingHours(Specification)"),
    ("schema_sameas_3", 10, "schema sameAs with 3+ links"),
    ("schema_rating", 10, "aggregateRating or Review schema"),
    ("faq_schema", 10, "FAQPage schema"),
    ("person_schema", 5, "Person or author schema"),
    ("nap_phone", 5, "phone number visible in page text"),
    ("nap_address", 5, "street address with city/state/zip visible in page text"),
    ("city_mentions_5", 5, "'Nashville' 5+ times in body text"),
    ("accreditation", 5, "Joint Commission/CARF/LegitScript mentioned"),
    ("meta_desc_70_160", 5, "meta description present, 70-160 chars"),
]
ORG_TYPES = {"Organization", "MedicalOrganization"}
LOCALBIZ_TYPES = {"LocalBusiness", "MedicalClinic", "MedicalBusiness", "Hospital"}
TERM_RE = re.compile(r"\b(nashville|tennessee|tn|rehab|detox|residential|inpatient|outpatient|iop|php|treatment|"
                     r"insurance|admissions)\b", re.I)
NAV_LOC_RE = re.compile(r"\blocations?\b|/locations?/|\bour (facilities|campuses|centers)\b", re.I)
NAV_PROG_RE = re.compile(r"\bprograms?\b|levels?[ -]of[ -]care|/programs?/|/treatment/|\btreatment\b|\bservices\b", re.I)
CHAT_HINTS = {"intercom": r"intercom", "drift": r"\bdrift\b|js\.driftt|drift\.com", "tawk": r"tawk\.to|\btawk",
              "livechat": r"livechat", "podium": r"podium", "olark": r"olark", "tidio": r"tidio",
              "zendesk": r"zopim|zdassets|zendesk", "crisp": r"crisp\.chat", "birdeye": r"birdeye",
              "smartsupp": r"smartsupp"}
FORM_EMBED_RE = re.compile(r"hbspt\.forms|gform|wpforms|jotform|typeform|formstack|ninja-forms|cognitoforms|"
                           r"formassembly|salesforce.*web-to-lead", re.I)
VIDEO_RE = re.compile(r"youtube\.com|youtu\.be|youtube-nocookie|vimeo\.com|wistia|vidyard|loom\.com|brightcove", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)")
STATEZIP_RE = re.compile(r"\b(?:TN|Tennessee|[A-Z]{2})\.?,?\s+\d{5}(?:-\d{4})?\b")
STREET_RE = re.compile(r"\b\d{1,6}\s+[\w .'-]{1,50}?\b(?:st|street|rd|road|ave|avenue|pike|blvd|boulevard|dr|drive|"
                       r"ln|lane|way|hwy|highway|pkwy|parkway|ct|court|cir|circle|pl|place|trl|trail|pk)\b", re.I)
TESTI_ATTR_RE = re.compile(r"testimonial|reviews?\b|review-|review_", re.I)
TESTI_HEAD_RE = re.compile(r"testimonial|\breviews?\b|what (our )?(clients|patients|alumni|families|people) (are )?say",
                           re.I)


def _types(node, out):
    if isinstance(node, dict):
        t = node.get("@type")
        out.extend(t if isinstance(t, list) else [t] if t else [])
    for v in (node.values() if isinstance(node, dict) else node if isinstance(node, list) else []):
        _types(v, out)


def extract(url, html, role):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    jsonld = []
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            _types(json.loads(s.string or s.get_text() or "{}"), jsonld)
        except Exception:
            jsonld.append("INVALID_JSON")
    tels = [a for a in soup.find_all("a", href=True) if a["href"].lower().startswith("tel:")]
    header, imgs = soup.find("header"), soup.find_all("img")
    header_tel = bool(header and header.find("a", href=re.compile(r"^tel:", re.I)))
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    h1s = [h.get_text(" ", strip=True) for h in soup.find_all("h1")]
    heads = [h.get_text(" ", strip=True) for h in soup.find_all(["h2", "h3", "h4", "summary", "button"])]
    q_heads = sum(1 for h in heads if h.endswith("?") and len(h) < 200)
    review_hints = len(soup.find_all(class_=REVIEW_RE)) + len(soup.find_all(id=REVIEW_RE))
    for t in soup(["script", "style", "noscript", "svg", "template"]):
        t.decompose()
    low = soup.get_text(" ", strip=True).lower()
    main = soup.find("main") or soup.find(attrs={"role": "main"}) or soup.find("article")
    if not main:
        for t in soup.find_all(["header", "footer", "nav", "aside"]):
            t.decompose()
        main = soup.body or soup
    main_words = len(re.findall(r"\w+", main.get_text(" ", strip=True)))
    row = {
        "url": url, "role": role, "host": urlparse(url).netloc.replace("www.", ""), "error": "",
        "title": title, "title_len": len(title),
        "title_service_and_geo": bool(SERVICE_RE.search(title) and GEO_RE.search(title)),
        "h1": h1s[0] if h1s else "", "h1_count": len(h1s), "word_count": main_words,
        "h2_count": len(soup.find_all("h2")), "question_headings": q_heads,
        "faq": q_heads >= 3 or "FAQPage" in jsonld, "jsonld_types": sorted(set(jsonld)),
        "tel_links": len(tels), "header_tel": header_tel, "forms": len(soup.find_all("form")),
        "insurers": [k for k, rx in INSURERS.items() if re.search(rx, low)],
        "mentions_24_7": bool(re.search(r"24\s*/\s*7|24\s+hours", low)),
        "accreditations": [k for k, rx in ACCRED.items() if re.search(rx, low)],
        "verify_insurance": bool(re.search(r"verify\s+(your\s+)?insurance|insurance\s+verification", low)),
        "review_hints": review_hints + len(re.findall(r"testimonial|google reviews?|\b\d\.\d\s*stars?", low)),
        "images": len(imgs), "images_with_alt": sum(1 for i in imgs if (i.get("alt") or "").strip())}
    try:
        row.update(analyze(url, html))
    except Exception as e:
        row["entity_error"] = f"analyze: {type(e).__name__}: {e}"[:200]
    return row


def _nodes(node, out):
    if isinstance(node, dict):
        out.append(node)
        for v in node.values():
            _nodes(v, out)
    elif isinstance(node, list):
        for v in node:
            _nodes(v, out)


def _ntypes(n):
    t = n.get("@type") if isinstance(n, dict) else None
    return {x.rsplit("/", 1)[-1].split(":")[-1] for x in (t if isinstance(t, list) else [t]) if isinstance(x, str)}


def _score(signals):
    score = sum(p for k, p, _ in ENTITY_SIGNALS if signals.get(k) == "yes")
    failed = [lbl for k, p, lbl in ENTITY_SIGNALS if signals.get(k) != "yes"]
    return score, failed


def analyze(url, html):
    """Entity signals (yes/no) + score, and on-page strategy signals, from raw HTML."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    nodes = []
    for s in soup.find_all("script", type=re.compile(r"ld\+json", re.I)):
        try:
            _nodes(json.loads(s.string or s.get_text() or "{}"), nodes)
        except Exception:
            pass
    types = set().union(*[_ntypes(n) for n in nodes]) if nodes else set()
    has = lambda k: any(n.get(k) not in (None, "", [], {}) for n in nodes)
    sameas = max([len(v) if isinstance(v, list) else 1 for v in (n.get("sameAs") for n in nodes) if v] or [0])
    rating_value = rating_count = None
    for n in nodes:
        ar = n if "AggregateRating" in _ntypes(n) else n.get("aggregateRating")
        ar = (ar[0] if ar else None) if isinstance(ar, list) else ar
        if isinstance(ar, dict) and ar.get("ratingValue") is not None:
            rating_value, rating_count = ar.get("ratingValue"), ar.get("reviewCount") or ar.get("ratingCount")
            break
    host = urlparse(url).netloc.lower().replace("www.", "")
    # scripts / iframes (before stripping) for chat widgets, form embeds, video
    script_blob = " ".join((s.get("src") or "") + " " + (s.string or "")[:20000] for s in soup.find_all("script")).lower()
    iframe_srcs = [(f.get("src") or f.get("data-src") or f.get("data-lazy-src") or "") for f in soup.find_all("iframe")]
    chat = sorted(k for k, rx in CHAT_HINTS.items() if re.search(rx, script_blob + " " + " ".join(iframe_srcs).lower()))
    video_hosts = sorted({m.group(0).lower().split(".")[0] for s in iframe_srcs for m in [VIDEO_RE.search(s)] if m})
    video_embeds = sum(1 for s in iframe_srcs if VIDEO_RE.search(s)) + len(soup.find_all("video")) + \
        len(soup.find_all(class_=re.compile(r"wistia_embed|lite-youtube|vimeo-embed", re.I))) + len(soup.find_all("lite-youtube"))
    meta = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    meta_desc = (meta.get("content") or "").strip() if meta else ""
    # nav
    navs = soup.find_all("nav") + soup.find_all(attrs={"role": "navigation"})
    if not navs:
        navs = soup.find_all("header") or soup.find_all(id=re.compile(r"menu|nav", re.I)) + \
            soup.find_all(class_=re.compile(r"\bmenu\b|\bnav", re.I))
    nav_txt = " ".join(n.get_text(" ", strip=True) + " " + " ".join(a.get("href", "") for a in n.find_all("a", href=True))
                       for n in navs)
    # internal links with city/service terms
    term_anchors, term_urls = 0, set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "tel:", "mailto:", "javascript:")):
            continue
        p = urlparse(urljoin(url, href))
        if p.netloc.lower().replace("www.", "") != host:
            continue
        if TERM_RE.search(p.path) or TERM_RE.search(a.get_text(" ", strip=True)):
            term_anchors += 1
            term_urls.add(p.path.rstrip("/") or "/")
    tels = [a for a in soup.find_all("a", href=True) if a["href"].lower().startswith("tel:")]
    hrefs_low = " ".join(a["href"].lower() for a in soup.find_all("a", href=True))
    forms = len(soup.find_all("form"))
    form_embed = bool(FORM_EMBED_RE.search(script_blob))
    insurer_logos = sum(1 for i in soup.find_all("img")
                        if any(re.search(rx, (i.get("alt") or "").lower()) for rx in INSURERS_EXT.values()))
    def _testi(tag):
        v = " ".join(tag.get("class") or []) + " " + (tag.get("id") or "")
        return bool(TESTI_ATTR_RE.search(v))
    matched = soup.find_all(lambda t: t.name in ("section", "div", "ul", "aside", "article") and _testi(t))
    top = [t for t in matched if not any(_testi(p) for p in t.parents if getattr(p, "name", None))]
    testi_heads = sum(1 for h in soup.find_all(["h2", "h3"]) if TESTI_HEAD_RE.search(h.get_text(" ", strip=True)))
    h2s = [re.sub(r"\s+", " ", h.get_text(" ", strip=True))[:100] for h in soup.find_all("h2")]
    h2s = [h for h in h2s if h]
    for t in soup(["script", "style", "noscript", "svg", "template"]):
        t.decompose()
    text = soup.get_text(" ", strip=True)
    low = text.lower()
    nap_address = any(STREET_RE.search(text[max(0, m.start() - 140):m.start()]) for m in STATEZIP_RE.finditer(text))
    city_n = len(re.findall(r"\b%s\b" % CITY, low))
    insurers = [k for k, rx in INSURERS_EXT.items() if re.search(rx, low)]
    verify = bool(re.search(r"verify\s+(your\s+)?(insurance|benefits|coverage)|insurance\s+verification|check\s+"
                            r"(your\s+)?(insurance|coverage)", low)) or bool(re.search(r"verify[-_]?(your[-_])?insurance|"
                                                                                     r"insurance[-_]verification", hrefs_low))
    yn = lambda b: "yes" if b else "no"
    sig = {
        "org_schema": yn(types & ORG_TYPES), "local_schema": yn(types & LOCALBIZ_TYPES),
        "schema_telephone": yn(has("telephone")), "schema_address": yn(has("address") or "PostalAddress" in types),
        "schema_geo": yn(has("geo") or "GeoCoordinates" in types),
        "schema_opening_hours": yn(has("openingHours") or has("openingHoursSpecification")),
        "schema_sameas_3": yn(sameas >= 3),
        "schema_rating": yn(rating_value is not None or types & {"AggregateRating", "Review"} or has("review")
                            or has("aggregateRating")),
        "faq_schema": yn("FAQPage" in types), "person_schema": yn("Person" in types or has("author")),
        "nap_phone": yn(PHONE_RE.search(text)), "nap_address": yn(nap_address),
        "city_mentions_5": yn(city_n >= 5), "accreditation": yn(any(re.search(rx, low) for rx in ACCRED.values())),
        "meta_desc_70_160": yn(70 <= len(meta_desc) <= 160)}
    score, failed = _score(sig)
    cta = (["tel"] if tels else []) + (["form"] if forms or form_embed else []) + \
        (["verify_insurance"] if verify else []) + (["chat"] if chat else [])
    strategy = {
        "url_path": urlparse(url).path or "/", "internal_term_links": term_anchors,
        "internal_term_link_urls": len(term_urls), "nav_found": bool(navs),
        "nav_locations": bool(NAV_LOC_RE.search(nav_txt)), "nav_programs": bool(NAV_PROG_RE.search(nav_txt)),
        "insurer_names": insurers, "insurer_count": len(insurers), "insurer_logos": insurer_logos,
        "cta_types": cta, "tel_links": len(tels), "forms": forms, "form_embed": form_embed, "chat_vendors": chat,
        "rating_value": rating_value, "rating_count": rating_count,
        "testimonial_sections": len(top) + testi_heads, "mentions_24_7": bool(re.search(r"24\s*/\s*7|24[\s-]hours?", low)),
        "video_embeds": video_embeds, "video_hosts": video_hosts, "h2_count": len(h2s), "h2s": h2s[:10],
        "city_mentions": city_n, "meta_description_len": len(meta_desc), "schema_types": sorted(types)}
    return {"entity_signals": sig, "entity_score": score, "entity_failed": failed, "entity_source": "fetch",
            "strategy": strategy}


def _fallback_entity(r):
    """Fetch failed: derive what we can from the saved row; the rest is 'unknown' (scores 0)."""
    t = set(r.get("jsonld_types") or [])
    yn = lambda b: "yes" if b else "no"
    sig = {k: "unknown" for k, _, _ in ENTITY_SIGNALS}
    sig.update({"org_schema": yn(t & ORG_TYPES), "local_schema": yn(t & LOCALBIZ_TYPES), "faq_schema": yn("FAQPage" in t),
                "person_schema": yn("Person" in t), "accreditation": yn(r.get("accreditations")),
                "schema_address": yn("PostalAddress" in t) if "PostalAddress" in t else "unknown",
                "schema_geo": "yes" if "GeoCoordinates" in t else "unknown",
                "schema_rating": "yes" if t & {"AggregateRating", "Review"} else "unknown"})
    score, failed = _score(sig)
    strategy = {"url_path": urlparse(r.get("url", "")).path or "/", "insurer_names": r.get("insurers", []),
                "insurer_count": len(r.get("insurers", [])), "tel_links": r.get("tel_links", 0), "forms": r.get("forms", 0),
                "cta_types": (["tel"] if r.get("tel_links") else []) + (["form"] if r.get("forms") else []) +
                             (["verify_insurance"] if r.get("verify_insurance") else []),
                "mentions_24_7": r.get("mentions_24_7"), "h2_count": r.get("h2_count"), "h2s": [],
                "schema_types": sorted(t)}
    return {"entity_signals": sig, "entity_score": score, "entity_failed": failed,
            "entity_source": "saved_json_fallback", "strategy": strategy}


def _competitor_urls(market):
    urls = []
    try:
        for r in (market or {}).get("serps", {}).get("results", []) or []:
            for it in [i for i in (r.get("items") or []) if i.get("type") in ("local_pack", "organic")]:
                u = it.get("url") or it.get("domain") or ""
                u = u if u.startswith("http") else ("https://" + u if u else "")
                if urlparse(u).netloc and u not in urls:
                    urls.append(u)
    except Exception:
        return []
    return urls


def _audited_urls(site):
    hi = [p for p in (site or {}).get("pages", {}).values() if getattr(p, "intent_weight", 0) >= 4 and getattr(p, "status", 0) == 200]
    def rank(p):
        path = urlparse(p.final_url or p.url).path or "/"
        return (PREFERRED_PATHS.index(path) if path in PREFERRED_PATHS else 99, -p.intent_weight)
    return [p.final_url or p.url for p in sorted(hi, key=rank)[:4]]


def _get(url, client, timeout):
    import requests
    get = client.get if client is not None else requests.get
    r = get(url, headers={"User-Agent": BROWSER_UA, "Accept": "text/html,*/*"}, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")
    return (r.url or url), r.text


def _fetch(url, role, client, timeout):
    try:
        final, html = _get(url, client, timeout)
        return extract(final, html, role)
    except Exception as e:
        return {"url": url, "role": role, "host": urlparse(url).netloc, "error": f"{type(e).__name__}: {e}"[:200]}


def _enrich(row, client):
    """Re-fetch a saved row to add entity/strategy fields; on failure fall back to the saved values. Never raises."""
    row = dict(row)
    try:
        final, html = _get(row["url"], client, 45 if row.get("role") == "audited" else 30)
        if row.get("error"):
            return extract(final, html, row.get("role", "competitor"))
        row.update(analyze(final, html))
        row.pop("entity_error", None)
    except Exception as e:
        row["entity_error"] = f"{type(e).__name__}: {e}"[:200]
        if row.get("entity_source") != "fetch" and not row.get("error"):
            row.update(_fallback_entity(row))
    return row


_yn = lambda v: "yes" if v else "no"


def _md(rows, notes):
    cols = ["Page", "Title len", "Svc+Geo title", "H1s", "Words", "H2s", "FAQ", "Schema types", "Tel (hdr)",
            "Forms", "Insurers", "24/7", "Accred.", "Verify ins.", "Review hints", "Img alt"]
    out = ["# Competitor page comparison", "",
           "Pages that win Nashville rehab SERPs vs the audited site's money pages (single fetch each, raw HTML, "
           "no JS rendering).", "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        b = "**" if r["role"] == "audited" else ""
        name = b + r["url"].split("//")[-1].rstrip("/") + b
        if r.get("error"):
            out.append(f"| {name} | fetch failed: {r['error'][:60]} |" + " |" * (len(cols) - 2)); continue
        out.append("| " + " | ".join(str(x) for x in [
            name, r["title_len"], _yn(r["title_service_and_geo"]), r["h1_count"], r["word_count"], r["h2_count"],
            _yn(r["faq"]), ", ".join(t for t in r["jsonld_types"] if t not in ("ListItem", "ImageObject"))[:80] or "-",
            f"{r['tel_links']} ({_yn(r['header_tel'])})", r["forms"], ", ".join(r["insurers"]) or "-",
            _yn(r["mentions_24_7"]), ", ".join(r["accreditations"]) or "-", _yn(r["verify_insurance"]),
            r["review_hints"], f"{r['images_with_alt']}/{r['images']}"]) + " |")
    out += ["", "## What the winners do that the audited site does not", ""] + [f"- {n}" for n in notes]
    return "\n".join(out) + "\n"


def _name(r):
    return r["url"].split("//")[-1].replace("www.", "").rstrip("/")


def _s(r):
    return r.get("strategy") or {}


def _strategy_bullets(r):
    s, e = _s(r), r.get("entity_signals") or {}
    path = s.get("url_path") or "/"
    geo_path = bool(GEO_RE.search(path))
    b = [(f"URL pattern: ranks with its homepage (`/`), so the whole domain is the Nashville page" if path == "/" else
          f"URL pattern: dedicated `{path}` page" + (" with the city/state in the path" if geo_path else "")) +
         f"; title \"{r.get('title', '')[:70]}\" ({'service + geo' if r.get('title_service_and_geo') else 'no service+geo combo'}), "
         f"H1 \"{r.get('h1', '')[:60]}\"."]
    h2s = s.get("h2s") or []
    b.append(f"Outline: {r.get('word_count', '?')} main-content words, {s.get('h2_count', r.get('h2_count'))} H2s"
             + (": " + " / ".join(f"\"{h[:45]}\"" for h in h2s[:5]) if h2s else "") + ".")
    chat = s.get("chat_vendors") or []
    b.append(f"CTAs: {', '.join(s.get('cta_types') or []) or 'none detected in raw HTML'}; {s.get('tel_links', 0)} tel: links"
             f"{' (one in <header>)' if r.get('header_tel') else ''}, {s.get('forms', 0)} <form>"
             f"{' + form embed script' if s.get('form_embed') else ''}"
             f"{', chat: ' + ', '.join(chat) if chat else ''}{', 24/7 stated' if s.get('mentions_24_7') else ''}"
             f"{', ' + str(s.get('video_embeds')) + ' video embed(s)' if s.get('video_embeds') else ''}.")
    rating = (f"aggregateRating {s.get('rating_value')} from {s.get('rating_count') or '?'} reviews in schema"
              if s.get("rating_value") is not None else "no rating in schema")
    b.append(f"Proof: entity score {r.get('entity_score', 'n/a')}/100; {rating}; {s.get('testimonial_sections', 0)} "
             f"testimonial/review blocks; accreditations: {', '.join(r.get('accreditations') or []) or 'none named'}; "
             f"{s.get('insurer_count', 0)} insurers named ({s.get('insurer_logos', 0)} insurer logos by alt text).")
    b.append(f"Local signals: '{CITY.title()}' x{s.get('city_mentions', '?')}; visible phone {e.get('nap_phone', '?')}, "
             f"street address {e.get('nap_address', '?')}; local schema type {e.get('local_schema', '?')}; "
             f"{s.get('internal_term_links', 0)} internal links with city/service terms "
             f"({s.get('internal_term_link_urls', 0)} unique URLs); nav exposes locations {_yn(s.get('nav_locations'))}, "
             f"programs {_yn(s.get('nav_programs'))}.")
    return b


def _copy_first(comp, aud):
    """Rank cheap, common competitor practices the audited pages lack: most competitors first, then cheapest."""
    if not comp or not aud:
        return []
    sig = lambda k: (lambda r: (r.get("entity_signals") or {}).get(k) == "yes")
    st = lambda k: (lambda r: bool(_s(r).get(k)))
    med = sorted(_s(r).get("internal_term_links") or 0 for r in comp)[len(comp) // 2]
    cost_lbl = {1: "low", 2: "medium", 3: "high"}
    cands = [
        ("FAQPage JSON-LD", sig("faq_schema"), 1, "wrap the existing question headings on each money page in FAQPage markup"),
        ("Organization/MedicalOrganization JSON-LD", sig("org_schema"), 1, "one sitewide node with name, url, logo, telephone"),
        ("Local entity type (LocalBusiness/MedicalClinic)", sig("local_schema"), 1,
         "MedicalClinic node per campus with telephone, PostalAddress, geo and openingHours"),
        ("sameAs with 3+ profiles", sig("schema_sameas_3"), 1, "list GBP, Facebook, LinkedIn, YouTube, Instagram in sameAs"),
        ("schema telephone", sig("schema_telephone"), 1, "add the admissions number as telephone on the entity node"),
        ("schema geo + openingHours", lambda r: sig("schema_geo")(r) and sig("schema_opening_hours")(r), 1,
         "add GeoCoordinates and openingHoursSpecification (24/7 admissions) to the entity node"),
        ("meta description 70-160 chars", sig("meta_desc_70_160"), 1, "write service + Nashville meta descriptions"),
        ("visible NAP (phone + street address)", lambda r: sig("nap_phone")(r) and sig("nap_address")(r), 1,
         "print the full street address and phone in the footer of every page"),
        ("accreditation named in text", sig("accreditation"), 1, "name Joint Commission/CARF/LegitScript with badges"),
        ("24/7 availability stated", st("mentions_24_7"), 1, "put '24/7 admissions' next to the header phone"),
        ("tel: link on page", st("tel_links"), 1, "make every phone number a tel: link, one in the header"),
        ("insurer logos with alt text", lambda r: (_s(r).get("insurer_logos") or 0) > 0, 1,
         "add an in-network logo strip with alt text naming each insurer"),
        ("Person/author schema", sig("person_schema"), 2, "add a clinical reviewer Person (name, credentials) to service pages"),
        ("'Nashville' 5+ times in body", sig("city_mentions_5"), 2, "work Nashville/Middle Tennessee into H2s and body copy"),
        ("'Verify insurance' CTA", lambda r: "verify_insurance" in (_s(r).get("cta_types") or []), 2,
         "add a 'Verify insurance' button linking to a short benefits form"),
        (f"{med}+ internal links with city/service terms", lambda r: (_s(r).get("internal_term_links") or 0) >= max(med, 1), 2,
         "link service pages to each other with service + Nashville anchors"),
        ("nav exposes a locations section", st("nav_locations"), 2, "add a Locations item to the main nav"),
        ("testimonial/review block", lambda r: (_s(r).get("testimonial_sections") or 0) > 0, 2,
         "add an alumni/family testimonial block to each money page"),
        ("aggregateRating/Review schema", sig("schema_rating"), 2,
         "mark up first-party reviews shown on the page with Review/AggregateRating"),
        ("chat widget", lambda r: bool(_s(r).get("chat_vendors")), 2, "add a staffed chat/text widget for admissions"),
        ("video embed", lambda r: (_s(r).get("video_embeds") or 0) > 0, 3, "embed a short campus/admissions video"),
    ]
    rows = []
    for label, pred, cost, fix in cands:
        cn, an = sum(1 for r in comp if pred(r)), sum(1 for r in aud if pred(r))
        if cn and cn / len(comp) > an / len(aud):
            rows.append((cn, cost, an, label, fix))
    rows.sort(key=lambda x: (-x[0], x[1], x[2]))
    return [f"**{label}**: {cn}/{len(comp)} competitors do it, {an}/{len(aud)} of our pages do (cost: {cost_lbl[cost]}). "
            f"Fix: {fix}." for cn, cost, an, label, fix in rows[:6]]


def _md_extra(rows, copy_items):
    out = ["", "## Entity scores", "",
           "0-100 from JSON-LD and visible-text signals in the raw HTML (no JS rendering). Points per signal: " +
           "; ".join(f"{lbl} {p}" for _, p, lbl in ENTITY_SIGNALS) + ". 'unknown' (audited-page fetch failed, values "
           "from the saved JSON) scores 0.", "", "| Page | Score | Failed signals |", "|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r.get("role") != "audited", -(r.get("entity_score") or 0))):
        b = "**" if r.get("role") == "audited" else ""
        if r.get("entity_score") is None:
            out.append(f"| {b}{_name(r)}{b} | n/a | {r.get('entity_error') or r.get('error') or 'not fetched'} |"); continue
        src = " (partial: fetch failed, saved values)" if r.get("entity_source") == "saved_json_fallback" else ""
        out.append(f"| {b}{_name(r)}{b} | {r['entity_score']}{src} | {', '.join(r.get('entity_failed') or []) or '-'} |")
    cols = ["Page", "URL path", "City/svc int. links (unique)", "Nav: locations / programs", "Insurers (logos)", "CTAs",
            "Schema rating", "Testimonial blocks", "24/7", "Videos", "H2s"]
    out += ["", "## On-page strategy signals", "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        s = _s(r)
        if not s:
            continue
        b = "**" if r.get("role") == "audited" else ""
        rv = f"{s.get('rating_value')} ({s.get('rating_count') or '?'})" if s.get("rating_value") is not None else "-"
        out.append("| " + " | ".join(str(x) for x in [
            f"{b}{_name(r)}{b}", f"`{s.get('url_path', '/')}`",
            f"{s.get('internal_term_links', '?')} ({s.get('internal_term_link_urls', '?')})",
            f"{_yn(s.get('nav_locations'))} / {_yn(s.get('nav_programs'))}",
            f"{s.get('insurer_count', 0)} ({s.get('insurer_logos', '?')})", ", ".join(s.get("cta_types") or []) or "-",
            rv, s.get("testimonial_sections", "?"), _yn(s.get("mentions_24_7")), s.get("video_embeds", "?"),
            s.get("h2_count", "?")]) + " |")
    out += ["", "## What each competitor's on-page strategy is", ""]
    for r in [r for r in rows if r.get("role") == "competitor" and not r.get("error") and r.get("strategy")]:
        out += [f"### {_name(r)}", ""] + [f"- {x}" for x in _strategy_bullets(r)] + [""]
    out += ["## What Cumberland Heights should copy first", "",
            "Ordered by how many competitors do it, then by cost; only items where competitors lead the audited pages.", ""]
    out += [f"{i}. {x}" for i, x in enumerate(copy_items, 1)] or ["- Not enough data (fetches failed)."]
    return "\n".join(out) + "\n"


def _atomic_write(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        fh.write(text)
    os.replace(tmp, path)


LOCAL_TYPES = {"LocalBusiness", "MedicalClinic", "MedicalBusiness", "Place", "City", "PostalAddress"}
CONV_KEYS = {"mentions_24_7", "verify_insurance", "header_tel", "insurers", "review_hints", "accreditations"}


def _compare(comp, aud):  # -> [(note, gap_key)] where competitors lead
    if not comp or not aud:
        return []
    out = []
    derived = {"h1_geo": lambda r: bool(GEO_RE.search(r.get("h1", ""))),
               "local_schema": lambda r: bool(LOCAL_TYPES & set(r.get("jsonld_types", [])))}
    checks = [("title_service_and_geo", "have a title naming a service and Nashville/Tennessee"),
              ("h1_geo", "name Nashville/Tennessee in the H1"),
              ("faq", "carry an FAQ block (3+ question headings or FAQPage schema)"),
              ("mentions_24_7", "state 24/7 / 24-hour availability"),
              ("verify_insurance", "show a 'verify insurance' call to action"),
              ("local_schema", "emit a local entity type in JSON-LD (LocalBusiness/MedicalClinic/Place/City)"),
              ("header_tel", "put a tel: link inside <header>")]
    for key, label in checks:
        f = derived.get(key, lambda r, k=key: bool(r.get(k)))
        cn, an = sum(1 for r in comp if f(r)), sum(1 for r in aud if f(r))
        if cn / len(comp) - an / len(aud) >= 0.2:
            out.append((f"{cn}/{len(comp)} competitor pages {label}; {an}/{len(aud)} audited pages do.", key))
    ci = sum(len(r["insurers"]) for r in comp) / len(comp)
    ai = sum(len(r["insurers"]) for r in aud) / len(aud)
    if ci - ai >= 1:
        out.append((f"Competitors name {ci:.1f} major insurers per page on average vs {ai:.1f} on ours.", "insurers"))
    acc_c, acc_a = sum(1 for r in comp if r["accreditations"]), sum(1 for r in aud if r["accreditations"])
    if acc_c / len(comp) - acc_a / len(aud) >= 0.2:
        out.append((f"{acc_c}/{len(comp)} competitor pages name Joint Commission/CARF/LegitScript in text; "
                    f"{acc_a}/{len(aud)} audited pages do.", "accreditations"))
    med = lambda rows, k: sorted(r[k] for r in rows)[len(rows) // 2]
    for key, label in [("review_hints", "review/testimonial markers"), ("word_count", "main-content words"),
                       ("title_len", "title characters"), ("h2_count", "H2 sections")]:
        cm, am = med(comp, key), med(aud, key)
        if cm > am * 1.2 and cm - am >= 2:
            out.append((f"Median competitor page has {cm} {label} vs {am} on the audited pages.", key))
    return out[:8]


def _entity_finding(comp, aud, common):
    cs = [r for r in comp if r.get("entity_score") is not None]
    as_ = [r for r in aud if r.get("entity_score") is not None]
    if not cs or not as_:
        return None
    ca, aa = sum(r["entity_score"] for r in cs) / len(cs), sum(r["entity_score"] for r in as_) / len(as_)
    if ca <= aa:
        return None
    ev = [f"Competitor average entity score {ca:.0f}/100 vs {aa:.0f}/100 on our money pages."]
    ev += [f"{_name(r)}: {r['entity_score']}/100" + (" (partial)" if r.get("entity_source") == "saved_json_fallback" else "")
           for r in sorted(cs + as_, key=lambda r: -r["entity_score"])]
    lead = []
    for k, p, lbl in ENTITY_SIGNALS:
        cn = sum(1 for r in cs if (r.get("entity_signals") or {}).get(k) == "yes")
        an = sum(1 for r in as_ if (r.get("entity_signals") or {}).get(k) == "yes")
        if cn / len(cs) > an / len(as_):
            lead.append(f"{lbl} ({cn}/{len(cs)} competitors vs {an}/{len(as_)} ours)")
    if lead:
        ev.append("Signals competitors have more often: " + "; ".join(lead[:6]) + ".")
    f = Finding(id="competitor_entity_gap",
                title=f"Our money pages score {aa:.0f}/100 on entity signals vs {ca:.0f}/100 for Nashville SERP competitors",
                evidence=ev,
                why_it_matters="Google and AI answer engines resolve 'rehab in Nashville' to entities: a page that states "
                               "who the provider is, where it is, how to reach it and what others say about it (schema + "
                               "visible NAP + reviews + accreditation) is easier to trust, cite and show in local results.",
                fix="Ship the 'copy first' list in competitor_pages.md: complete the Organization/MedicalClinic JSON-LD "
                    "(telephone, PostalAddress, geo, openingHours, sameAs), add FAQPage and Review markup where the "
                    "content exists, and print NAP + accreditation in visible text on every money page.",
                **common)
    f.score()
    return f


def run(site: dict, market: dict | None, out_dir: str, client=None) -> list[Finding]:
    try:
        os.makedirs(out_dir, exist_ok=True)
        jpath, mpath = os.path.join(out_dir, "competitor_pages.json"), os.path.join(out_dir, "competitor_pages.md")
        if os.path.exists(jpath):
            with open(jpath) as fh:
                rows = json.load(fh).get("pages", [])
        else:
            comp_urls = _competitor_urls(market)[:8] or FALLBACK_COMPETITORS
            aud_urls = _audited_urls(site) or [site.get("start_url", "")]
            rows = []
            for u, role, t in [(u, "competitor", 30) for u in comp_urls] + [(u, "audited", 45) for u in aud_urls if u]:
                rows.append(_fetch(u, role, client, t))
                time.sleep(1)
        # add entity + strategy fields to saved rows that lack a successful analysis (parallel, never raises)
        try:
            need = [i for i, r in enumerate(rows) if r.get("entity_source") != "fetch"]
            if need:
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=min(6, len(need))) as ex:
                    for i, new in zip(need, ex.map(lambda i: _enrich(rows[i], client), need)):
                        rows[i] = new
        except Exception:
            pass
        comp = [r for r in rows if r["role"] == "competitor" and not r.get("error")]
        aud = [r for r in rows if r["role"] == "audited" and not r.get("error")]
        gaps = _compare(comp, aud)
        notes = [n for n, _ in gaps] or ["Not enough pages fetched, or no attribute where competitors lead by 20+ pts."]
        try:
            copy_items = _copy_first(comp, aud)
        except Exception:
            copy_items = []
        md = _md(rows, notes)
        try:
            md += _md_extra(rows, copy_items)
        except Exception as e:
            md += f"\n_Entity/strategy section failed: {type(e).__name__}: {e}_\n"
        _atomic_write(jpath, json.dumps({"pages": rows, "observations": notes, "copy_first": copy_items,
                                         "entity_signal_points": {k: p for k, p, _ in ENTITY_SIGNALS}}, indent=2,
                                        default=str))
        _atomic_write(mpath, md)
        common = dict(category="content", confidence="medium", severity=3, intent_weight=5,
                      pages=[r["url"] for r in aud], page_count=len(aud),
                      check_first="GSC: queries like 'rehab nashville' / 'detox nashville' for these URLs; "
                                  "impressions at position 8-20 mean relevant but out-competed.")
        specs = [
            ("competitor_content_gap", [n for n, k in gaps if k not in CONV_KEYS],
             "Nashville SERP winners target the city and structure content more explicitly than our money pages",
             "Ranking pages put service + Nashville/Tennessee in title/H1, mark up a local entity and answer "
             "objections in FAQ form, which matches local intent and is easier for AI answers to extract.",
             "Rewrite money-page titles/H1s as service + Nashville/Tennessee, add a 5-8 question FAQ with FAQPage "
             "markup, and add MedicalClinic/LocalBusiness JSON-LD to service pages."),
            ("competitor_trust_cta_gap", [n for n, k in gaps if k in CONV_KEYS],
             "Nashville SERP winners show more availability, insurance and proof signals on-page",
             "Admissions searchers decide on 'can I start now, will insurance cover it, is it legit'; "
             "competitor landing pages answer that before the first scroll.",
             "Add a 24/7 admissions line, named-insurer strip with a 'Verify insurance' CTA, and reviews/"
             "testimonials plus accreditation badges on each money page."),
        ]
        out = []
        for fid, ev, title, why, fix in specs:
            if ev:
                f = Finding(id=fid, title=title, evidence=ev, why_it_matters=why, fix=fix, **common)
                f.score()
                out.append(f)
        try:
            ef = _entity_finding(comp, aud, common)
            if ef:
                out.append(ef)
        except Exception:
            pass
        return out[:3]
    except Exception:
        return []
