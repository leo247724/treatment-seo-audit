"""On-page scorecard for high-intent pages (home, admissions/insurance/contact, program, location).

run(site, market, out_dir, client=None) -> list[Finding]; writes <out_dir>/onpage.md. Never raises.
"""
import os
import re
from collections import Counter
from urllib.parse import urlparse

from .models import Finding, Page

SERVICE = r"rehab|treatment|detox|residential|inpatient|outpatient|\biop\b|\bphp\b|addiction|alcohol|drug|" \
          r"recovery|program|therapy|mental health|dual diagnosis|co-occurring|opioid|substance|sober|counsel"
PLACE = ["nashville", "tennessee", r"\btn\b"]
CTA = r"\bcall|verify|admission|24/7"
RICH_SCHEMA = {"MedicalClinic", "MedicalBusiness", "FAQPage", "LocalBusiness"}
# Blog/resource/event/fundraising URLs that classify.py tags as program/conversion via words like "sober" or
# "what-to-expect"; they are not where a Nashville rehab search should land.
SKIP_PATH = re.compile(r"/wp-content/|/resources/(?!location/)|/blog/|/news|/podcast|/event|/tag/|/category/|/author/|"
                       r"/giving/|/donate|open-mic|retreat|summit|sober-space|-\d+/?$")
BRAND = "Cumberland Heights"

# (id, label, weight). Weights sum to 100; checks that do not apply are dropped from the denominator.
CHECKS = [
    ("title_present", "Title present", 5),
    ("title_length", "Title 30-60 chars", 8),
    ("title_terms", "Title has service + place term", 12),
    ("meta_present", "Meta description present", 4),
    ("meta_length", "Meta description 70-160 chars", 6),
    ("meta_cta", "Meta description has CTA (call/verify/admissions/24/7)", 5),
    ("h1", "Exactly one H1 with a service term", 10),
    ("h2", "3+ H2s", 5),
    ("words", "Enough main content words", 8),
    ("faq", "FAQ block present", 6),
    ("header_tel", "Tel link in header", 8),
    ("form", "Form on admissions/insurance/contact", 5),
    ("schema", "Medical/Local/FAQ schema beyond Organization/WebPage", 7),
    ("img_alt", "80%+ images have alt text", 3),
    ("links", "10+ internal links out", 3),
    ("canonical", "Self-referencing canonical", 3),
    ("indexable", "Not noindex", 2),
]
LABEL = {c[0]: c[1] for c in CHECKS}


def _has(pattern, text):
    return bool(re.search(pattern, (text or "").lower()))


def _place_re(market):
    terms = list(PLACE)
    if isinstance(market, dict):
        for k in ("city", "state", "state_code"):
            v = market.get(k)
            if isinstance(v, str) and v.strip():
                terms.append(r"\b" + re.escape(v.strip().lower()) + r"\b")
    return "|".join(terms)


def _norm(u):
    p = urlparse((u or "").strip())
    return (p.netloc.lower().replace("www.", ""), p.path.rstrip("/") or "/")


def _min_words(p):
    return 500 if p.page_type == "program" else 300


def score_page(p: Page, place_re: str) -> dict:
    t, md, url = p.title or "", p.meta_description or "", p.final_url or p.url
    path = urlparse(url).path.lower()
    alt_ok = p.images == 0 or (p.images - p.images_no_alt) / p.images >= 0.8
    res = {
        "title_present": bool(t.strip()),
        "title_length": 30 <= len(t) <= 60,
        "title_terms": _has(SERVICE, t) and _has(place_re, t),
        "meta_present": bool(md.strip()),
        "meta_length": 70 <= len(md) <= 160,
        "meta_cta": _has(CTA, md),
        "h1": len(p.h1s) == 1 and _has(SERVICE, p.h1s[0]),
        "h2": p.h2_count >= 3,
        "words": p.main_word_count >= _min_words(p),
        "faq": bool(p.has_faq) or "FAQPage" in (p.jsonld_types or []),
        "header_tel": bool(p.header_has_tel),
        "form": (p.forms > 0) if re.search(r"admission|insurance|contact|verify", path) else None,
        "schema": bool(RICH_SCHEMA & set(p.jsonld_types or [])),
        "img_alt": alt_ok,
        "links": len(p.internal_links or []) >= 10,
        "canonical": bool(p.canonical) and _norm(p.canonical) == _norm(url),
        "indexable": not p.noindex,
    }
    w = {c: wt for c, _, wt in CHECKS if res[c] is not None}
    got = sum(wt for c, wt in w.items() if res[c])
    failed = [c for c, _, _ in CHECKS if res[c] is False]
    return {"url": url, "page": p, "type": p.page_type, "score": round(100 * got / max(sum(w.values()), 1)),
            "failed": failed, "res": res}


def _program_name(p: Page) -> str:
    name = re.split(r"\s+[-|–]\s+", p.title or "")[0].strip()
    if not name or len(name) > 32 or name.lower() == "home":
        slug = [s for s in urlparse(p.final_url or p.url).path.split("/") if s]
        name = slug[-1].replace("-", " ").title() if slug else "Addiction Treatment"
    name = re.sub(r"\s*\(.*?\)", "", name)
    name = re.sub(r"\b(Iop|Php)\b", lambda m: m.group(0).upper(), name)
    name = re.sub(r"\s*[-|–:]?\s*" + re.escape(BRAND) + r"\s*[-|–:]?\s*", " ", name, flags=re.I).strip()
    return name or "Addiction Treatment"


def suggest_title(p: Page) -> str:
    name = "Addiction Treatment" if p.page_type == "home" else _program_name(p)
    t = f"{name} in Nashville, TN | {BRAND}"
    if len(t) > 60:
        t = f"{name} in Nashville | {BRAND}"
    if len(t) > 60:
        t = f"{name[:60 - len(f' in Nashville | {BRAND}')].rstrip()} in Nashville | {BRAND}"
    return t


def _f(**kw) -> Finding:
    kw.setdefault("confidence", "medium")
    kw.setdefault("page_count", len(kw.get("pages", [])))
    return Finding(**kw)


GSC = ("GSC Performance > Pages, sorted by impressions: compare CTR by page for these URLs against "
       "site average and position; pages ranking 4-15 with below-average CTR are the first rewrites.")


def build_findings(cards, place_re):
    out, n = [], len(cards)
    if not n:
        return out
    bad_title = sorted((c for c in cards if {"title_terms", "title_length"} & set(c["failed"])),
                       key=lambda c: (c["type"] != "home", c["type"] != "conversion", c["score"]))
    if bad_title:
        no_place = sum(1 for c in cards if not _has(place_re, c["page"].title))
        ev = [f"{len(bad_title)}/{n} high-intent pages fail the title checks; {no_place}/{n} titles have no "
              f"Nashville/Tennessee/TN term"]
        ev += [f"\"{c['page'].title}\" ({len(c['page'].title)} chars) -> {c['url']}" for c in bad_title[:6]]
        out.append(_f(id="onpage_titles_no_local_service", category="content",
                      title=f"{len(bad_title)} of {n} high-intent page titles miss the service + Nashville terms people search",
                      severity=3, intent_weight=5, pages=[c["url"] for c in bad_title[:8]],
                      page_count=len(bad_title), evidence=ev,
                      why_it_matters="Searchers type 'rehab nashville' / 'detox nashville'; titles like 'Home - Cumberland "
                                     "Heights' neither match the query nor earn the click, so fewer people reach the page "
                                     "with the admissions number and fewer calls start.",
                      fix="Rewrite titles to '<Program> in Nashville, TN | Cumberland Heights' (30-60 chars), starting "
                          "with the homepage and program pages; keep the H1 aligned with the same service term.",
                      check_first=GSC, confidence="high"))
    bad_meta = [c for c in cards if {"meta_length", "meta_cta"} & set(c["failed"])]
    if bad_meta:
        lens = sorted(len(c["page"].meta_description) for c in cards)
        no_cta = sum(1 for c in cards if "meta_cta" in c["failed"])
        ev = [f"{len(bad_meta)}/{n} pages have a meta description outside 70-160 chars or with no call/verify/"
              f"admissions/24/7 wording ({no_cta} lack a CTA); median length {lens[len(lens) // 2]} chars"]
        ev += [f"{c['url']}: {len(c['page'].meta_description)} chars, \"{c['page'].meta_description[:90]}...\""
               for c in bad_meta[:4]]
        out.append(_f(id="onpage_meta_no_cta", category="content",
                      title=f"{len(bad_meta)} of {n} high-intent meta descriptions are truncated or carry no call to action",
                      severity=2, intent_weight=5, pages=[c["url"] for c in bad_meta[:8]], page_count=len(bad_meta),
                      evidence=ev,
                      why_it_matters="The snippet is the last thing a family reads before choosing whom to call; a cut-off "
                                     "description with no '24/7 admissions' or 'verify insurance' line loses that call to "
                                     "a competitor whose snippet asks for it.",
                      fix="Write 140-155 char descriptions per page: service + Nashville + one proof point + 'Call 24/7' "
                          "or 'Verify insurance in minutes'.",
                      check_first=GSC))
    depth = [c for c in cards if len({"faq", "schema", "words", "h1"} & set(c["failed"])) >= 2]
    if depth:
        cnt = Counter(f for c in depth for f in c["failed"] if f in ("faq", "schema", "words", "h1"))
        ev = [f"{len(depth)}/{n} pages fail 2+ depth checks: " + ", ".join(f"{LABEL[k]} x{v}" for k, v in cnt.most_common())]
        ev += [f"{c['url']}: score {c['score']}, {c['page'].main_word_count} main words, H1 {c['page'].h1s[:1]}"
               for c in sorted(depth, key=lambda c: c["score"])[:5]]
        out.append(_f(id="onpage_thin_program_pages", category="content",
                      title=f"{len(depth)} program/admissions pages lack FAQ, medical schema or depth to rank for Nashville treatment terms",
                      severity=3, intent_weight=4, pages=[c["url"] for c in depth[:8]], page_count=len(depth),
                      evidence=ev,
                      why_it_matters="Pages that do not answer cost, insurance, length-of-stay and 'what happens when I "
                                     "call' questions rank below directories and lose callers who are ready to admit.",
                      fix="Add a 5-8 question FAQ block with FAQPage schema, MedicalClinic schema with the Nashville "
                          "address, a service-term H1, and 500+ words of program detail on each page.",
                      check_first=GSC))
    return out[:3]


def _c(text):
    return str(text).replace("|", "\\|")


def write_md(cards, findings, out_dir):
    n = len(cards)
    avg = round(sum(c["score"] for c in cards) / n, 1) if n else 0
    fails = Counter(f for c in cards for f in c["failed"])
    worst_prog = [c for c in cards if c["type"] == "program"][:3]
    home = [c for c in cards if c["type"] == "home"]
    L = ["# On-page scorecard (high-intent pages)", "",
         f"- Pages scored: {n} (intent weight >= 4, HTTP 200, blog/resource and wp-content URLs excluded)",
         f"- Average score: **{avg}/100**", "", "## Most common failed checks", "", "| Check | Pages failing |", "|---|---|"]
    L += [f"| {LABEL[k]} | {v}/{n} |" for k, v in fails.most_common()]
    L += ["", "## 10 lowest-scoring pages", "", "| Score | Type | URL | Title |", "|---|---|---|---|"]
    L += [f"| {c['score']} | {c['type']} | {c['url']} | {_c(c['page'].title)} |" for c in cards[:10]]
    L += ["", "## Title rewrites", "", "| Page | Current title | Suggested title |", "|---|---|---|"]
    L += [f"| {c['url']} | {_c(c['page'].title)} ({len(c['page'].title)}) | {_c(suggest_title(c['page']))} "
          f"({len(suggest_title(c['page']))}) |" for c in home + worst_prog]
    L += ["", "## Findings", ""]
    for f in findings:
        L += [f"### {f.title}", "", *[f"- {e}" for e in f.evidence], "", f"**Why:** {f.why_it_matters}", "",
              f"**Fix:** {f.fix}", "", f"**Check first:** {f.check_first}", ""]
    L += ["## Full scorecard (lowest first)", "", "| Score | Type | URL | Failed checks |", "|---|---|---|---|"]
    L += [f"| {c['score']} | {c['type']} | {c['url']} | {'; '.join(LABEL[x] for x in c['failed']) or '-'} |"
          for c in cards]
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "onpage.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")
    return {"avg": avg, "fails": fails, "worst": cards[:3], "title_suggestions": [suggest_title(c["page"]) for c in home + worst_prog]}


def select_pages(site) -> list[Page]:
    out = []
    for p in (site.get("pages") or {}).values():
        url = p.final_url or p.url
        if p.status != 200 or not p.is_html or p.intent_weight < 4 or SKIP_PATH.search(urlparse(url).path.lower()):
            continue
        out.append(p)
    return out


def run(site: dict, market: dict | None, out_dir: str, client=None) -> list[Finding]:
    try:
        place_re = _place_re(market)
        cards = sorted((score_page(p, place_re) for p in select_pages(site)), key=lambda c: (c["score"], c["url"]))
        findings = build_findings(cards, place_re)
        for f in findings:
            f.score()
        write_md(cards, findings, out_dir)
        return findings
    except Exception as e:  # never raise into the pipeline
        print(f"[onpage] skipped: {e!r}")
        return []
