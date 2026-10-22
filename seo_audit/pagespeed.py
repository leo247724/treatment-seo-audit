"""Core Web Vitals via the free Google PageSpeed Insights API (no key needed for a handful of calls)."""
import logging
import requests
from .models import Finding
from .checks import _f, indexable

log = logging.getLogger("audit")
PSI = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


def pick_pages(site, n=4):
    idx = indexable(site)
    chosen, types = [], set()
    for p in sorted(idx, key=lambda p: (-p.intent_weight, p.page_type)):
        if p.page_type not in types:
            chosen.append(p.final_url)
            types.add(p.page_type)
        if len(chosen) >= n:
            break
    return chosen


def run_psi(url, key=None, strategy="mobile", timeout=150):
    params = {"url": url, "strategy": strategy, "category": "PERFORMANCE"}
    if key:
        params["key"] = key
    r = requests.get(PSI, params=params, timeout=timeout)
    r.raise_for_status()
    d = r.json()
    lr = d.get("lighthouseResult", {})
    audits = lr.get("audits", {})
    field = d.get("loadingExperience", {}).get("metrics", {})

    def fm(k):
        m = field.get(k)
        return m.get("percentile") if m else None

    cls_field = fm("CUMULATIVE_LAYOUT_SHIFT_SCORE")
    score = lr.get("categories", {}).get("performance", {}).get("score")
    return {"url": url, "strategy": strategy,
            "perf_score": round(score * 100) if score is not None else None,
            "lab_lcp_s": round((audits.get("largest-contentful-paint", {}).get("numericValue") or 0) / 1000, 1),
            "lab_cls": round(audits.get("cumulative-layout-shift", {}).get("numericValue") or 0, 3),
            "lab_tbt_ms": round(audits.get("total-blocking-time", {}).get("numericValue") or 0),
            "field_lcp_ms": fm("LARGEST_CONTENTFUL_PAINT_MS"),
            "field_inp_ms": fm("INTERACTION_TO_NEXT_PAINT"),
            "field_cls": (cls_field / 100) if cls_field is not None else None,
            "field_overall": d.get("loadingExperience", {}).get("overall_category")}


def run_all(site, key=None, n=4):
    results = []
    for url in pick_pages(site, n):
        try:
            log.info("PageSpeed (mobile): %s", url)
            results.append(run_psi(url, key))
        except Exception as e:
            log.warning("PSI failed for %s: %s", url, e)
            results.append({"url": url, "error": str(e)[:120]})
    return results


def check_pagespeed(site, results):
    bad, ev = [], []
    pages = {p.final_url: p for p in indexable(site)}
    for r in results:
        if "error" in r:
            ev.append(f"{r['url']}: PSI error ({r['error'][:60]})")
            continue
        fails = []
        if r["field_lcp_ms"] and r["field_lcp_ms"] > 2500:
            fails.append(f"field LCP {r['field_lcp_ms']/1000:.1f}s")
        if r["field_inp_ms"] and r["field_inp_ms"] > 200:
            fails.append(f"field INP {r['field_inp_ms']}ms")
        if r["field_cls"] is not None and r["field_cls"] > 0.1:
            fails.append(f"field CLS {r['field_cls']:.2f}")
        if r["perf_score"] is not None and r["perf_score"] < 50:
            fails.append(f"lab performance score {r['perf_score']}/100 (LCP {r['lab_lcp_s']}s, TBT {r['lab_tbt_ms']}ms)")
        line = f"{r['url']}: score {r['perf_score']}, lab LCP {r['lab_lcp_s']}s, field LCP {r['field_lcp_ms']}ms, INP {r['field_inp_ms']}ms, CLS {r['field_cls']} ({r['field_overall'] or 'no field data'})"
        ev.append(line)
        if fails:
            bad.append((r["url"], fails))
    if not bad:
        return []
    weight = max((pages[u].intent_weight for u, _ in bad if u in pages), default=4)
    worst = min((r["perf_score"] for r in results if "error" not in r and r["perf_score"] is not None), default=100)
    sev = 4 if worst < 40 or any("field" in f for _, fs in bad for f in fs) else 3
    return [_f(id="core_web_vitals", category="technical", title="Slow mobile pages (Core Web Vitals / PageSpeed)",
               severity=sev, intent_weight=weight, pages=[u for u, _ in bad], page_count=len(bad), evidence=ev,
               why_it_matters="Crisis searches are on phones, often on cellular. Every extra second before the phone number renders loses callers; field CWV failures also cost rankings on mobile.",
               fix="Compress/lazy-load hero media, defer third-party scripts (chat widgets, tag managers), inline critical CSS, serve the header phone number in the first paint.",
               check_first="GSC: Core Web Vitals report (mobile) for the share of 'poor' URLs. Call tracking: call rate by device.",
               confidence="high")]
