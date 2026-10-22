"""Competitor page comparison: what the pages winning the Nashville rehab SERPs do that the audited site does not."""
import json, os, re, time
from urllib.parse import urlparse
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
ACCRED = {"joint_commission": r"joint\s+commission", "carf": r"\bcarf\b", "legitscript": r"legitscript"}
REVIEW_RE = re.compile(r"testimonial|review|stars?\b|rated\s+\d|\d\.\d\s*(out of|/)\s*5", re.I)


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
    return {
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


def _fetch(url, role, client, timeout):
    try:
        import requests
        get = client.get if client is not None else requests.get
        r = get(url, headers={"User-Agent": BROWSER_UA, "Accept": "text/html,*/*"}, timeout=timeout)
        if r.status_code != 200:
            return {"url": url, "role": role, "host": urlparse(url).netloc, "error": f"HTTP {r.status_code}"}
        return extract(r.url or url, r.text, role)
    except Exception as e:
        return {"url": url, "role": role, "host": urlparse(url).netloc, "error": f"{type(e).__name__}: {e}"[:200]}


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
        comp = [r for r in rows if r["role"] == "competitor" and not r.get("error")]
        aud = [r for r in rows if r["role"] == "audited" and not r.get("error")]
        gaps = _compare(comp, aud)
        notes = [n for n, _ in gaps] or ["Not enough pages fetched, or no attribute where competitors lead by 20+ pts."]
        with open(jpath, "w") as fh:
            json.dump({"pages": rows, "observations": notes}, fh, indent=2)
        with open(mpath, "w") as fh:
            fh.write(_md(rows, notes))
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
        return out[:2]
    except Exception:
        return []
