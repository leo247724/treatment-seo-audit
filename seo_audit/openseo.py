"""Market data through OpenSEO's MCP endpoint (DataForSEO-backed): ranked keywords, SERPs, local pack,
Google Maps, backlinks and AI Overview citations. This is the off-site half of the audit."""
import json
import logging
import os
import re
from collections import Counter, defaultdict
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

from .checks import _f, html_pages, indexable
from .classify import classify
from .crawl import norm_host, UA

log = logging.getLogger("audit")


class OpenSEO:
    """Minimal MCP client: one JSON-RPC POST per tool call (the server needs no session)."""

    def __init__(self, url, project_id, timeout=180):
        self.url, self.project_id, self.timeout = url, project_id, timeout
        self.s = requests.Session()
        self.s.headers.update({"Accept": "application/json, text/event-stream", "Content-Type": "application/json",
                               "User-Agent": UA})

    def call(self, name, arguments=None):
        body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": name, "arguments": {"projectId": self.project_id, **(arguments or {})}}}
        r = self.s.post(self.url, json=body, timeout=self.timeout)
        r.raise_for_status()
        d = r.json()
        if "error" in d:
            raise RuntimeError(d["error"])
        res = d["result"]
        if res.get("isError"):
            raise RuntimeError(str(res.get("content"))[:300])
        if "structuredContent" in res:
            return res["structuredContent"]
        return json.loads(res["content"][0]["text"])


def geocode(place):
    """City centre for Google Maps rank checks (free OpenStreetMap Nominatim; one request)."""
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search", params={"q": place, "format": "json", "limit": 1},
                         headers={"User-Agent": UA}, timeout=20)
        hit = r.json()[0]
        return float(hit["lat"]), float(hit["lon"])
    except Exception as e:
        log.warning("geocode failed for %r: %s", place, e)
        return None


def _read_cache(path):
    """Cached JSON, or None when the file is missing, unreadable or an old {"error": ...} stub (never data)."""
    try:
        with open(path) as fh:
            d = json.load(fh)
    except (OSError, ValueError):
        return None
    return None if isinstance(d, dict) and "error" in d else d


def _cached(out_dir, name, reuse, fn):
    path = os.path.join(out_dir, "openseo", f"{name}.json")
    if reuse:
        d = _read_cache(path)
        if d is not None:
            return d
    try:
        data = fn()
    except AttributeError:
        log.warning("OpenSEO %s: no endpoint configured and no cached file at %s", name, path)
        return {"error": "no OpenSEO endpoint configured"}
    except Exception as e:
        log.warning("OpenSEO %s failed: %s", name, str(e)[:160])
        return {"error": str(e)[:300]}  # in-memory only: never cache a failure over good (or future) data
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(data, fh, indent=1)
    return data


def fetch_all(client, host, brand, city, state, out_dir, reuse=False):
    place = f"{city}, {state}" if city else ""
    q = []
    if city:
        q = [f"alcohol rehab {city} {state}".strip(), f"drug rehab {city}", f"detox {city} {state}".strip(),
             f"inpatient rehab {city} {state}".strip(), f"rehab centers {city}"]
    comp_kw = q + ([f"addiction treatment {city}", f"residential treatment {city} {state}".strip(),
                    f"iop {city} {state}".strip(), f"outpatient rehab {city}"] if city else [])
    data = {"host": host, "brand": brand, "city": city, "state": state, "queries": q}
    data["overview"] = _cached(out_dir, "domain_overview", reuse, lambda: client.call("get_domain_overview", {"domain": host}))
    data["backlinks"] = _cached(out_dir, "backlinks_overview", reuse, lambda: client.call("get_backlinks_overview", {"target": host}))
    data["ranked_organic"] = _cached(out_dir, "ranked_keywords_organic", reuse, lambda: client.call(
        "get_ranked_keywords", {"target": host, "limit": 100, "sortBy": "traffic_estimate", "resultTypes": ["organic"]}))
    data["ranked_aio"] = _cached(out_dir, "ranked_keywords_ai_overview", reuse, lambda: client.call(
        "get_ranked_keywords", {"target": host, "limit": 100, "sortBy": "search_volume", "resultTypes": ["ai_overview_reference"]}))
    data["ranked_local"] = _cached(out_dir, "ranked_keywords_local_pack", reuse, lambda: client.call(
        "get_ranked_keywords", {"target": host, "limit": 50, "sortBy": "search_volume", "resultTypes": ["local_pack"]}))
    if q:
        data["serps"] = _cached(out_dir, "serp_results", reuse, lambda: client.call(
            "get_serp_results", {"queries": [{"keyword": k} for k in q + [brand]]}))
        data["competitors"] = _cached(out_dir, "serp_competitors", reuse, lambda: client.call(
            "find_serp_competitors", {"keywords": comp_kw, "limit": 15}))
        maps_names = {kw: f"maps_{kw.replace(' ', '_')}" for kw in ("alcohol rehab", "drug rehab")}
        all_cached = reuse and all(_read_cache(os.path.join(out_dir, "openseo", f"{n}.json")) is not None
                                   for n in maps_names.values())
        ll = None if all_cached else geocode(place)  # no network round-trip when the maps cache is complete
        if ll or all_cached:
            data["maps"] = {}
            for kw, name in maps_names.items():
                data["maps"][kw] = _cached(out_dir, name, reuse, lambda kw=kw: client.call(
                    "get_local_serp_results", {"keyword": kw, "near": {"latitude": ll[0], "longitude": ll[1], "zoom": 11},
                                               "depth": 20, "device": "mobile"}))
    return data


# ------------------------------------------------------------------ helpers
def _rows(block):
    return (block or {}).get("keywords", []) if isinstance(block, dict) else []


def _kw(row):
    kd = row.get("keyword_data") or {}
    se = (row.get("ranked_serp_element") or {}).get("serp_item") or {}
    ki = kd.get("keyword_info") or {}
    return {"keyword": kd.get("keyword") or "", "volume": ki.get("search_volume") or 0,
            "cpc": ki.get("cpc") or 0, "intent": (kd.get("search_intent_info") or {}).get("main_intent"),
            "rank": se.get("rank_group"), "abs": se.get("rank_absolute"), "etv": se.get("etv") or 0,
            "url": se.get("url") or "", "type": se.get("type"), "title": se.get("title"), "phone": se.get("phone"),
            "rating": (se.get("rating") or {}).get("value"), "votes": (se.get("rating") or {}).get("votes_count")}


def _page_type(url):
    return classify(url)[0]


def _strip_utm(url):
    """Drop utm_* tracking parameters (and the fragment) but keep meaningful query parameters such as ?page_id=."""
    p = urlparse(url or "")
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
    return urlunparse(p._replace(query=urlencode(q), fragment=""))


# ------------------------------------------------------------------ checks
def check_intent_mix(site, data):
    rows = [_kw(r) for r in _rows(data.get("ranked_organic"))]
    if not rows:
        return []
    by_type, by_url = Counter(), defaultdict(lambda: {"etv": 0, "kws": []})
    for r in rows:
        t = _page_type(r["url"])
        by_type[t] += r["etv"]
        by_url[r["url"]]["etv"] += r["etv"]
        by_url[r["url"]]["kws"].append(r["keyword"])
    total = sum(by_type.values()) or 1
    info_share = (by_type["content"] + by_type["archive"]) / total
    money_share = (by_type["home"] + by_type["conversion"] + by_type["local"] + by_type["program"]) / total
    top = sorted(by_url.items(), key=lambda kv: -kv[1]["etv"])[:5]
    ev = [f"Top {len(rows)} ranking keywords by estimated traffic (DataForSEO): {info_share:.0%} of estimated visits land on blog/archive pages, "
          f"{money_share:.0%} on home/program/location/admissions pages",
          f"Site-wide estimate: {(data.get('overview') or {}).get('organicTraffic')} visits/mo across {(data.get('overview') or {}).get('organicKeywords')} keywords"]
    ev += [f"{u.replace('https://', '')}: ~{v['etv']:.0f} visits/mo from e.g. '{v['kws'][0]}'" for u, v in top]
    if info_share < 0.6:
        return []
    return [_f(id="os_intent_mix", category="content", title="Organic traffic is mostly informational blog visits, not local treatment seekers",
               severity=3, intent_weight=4, pages=[u for u, _ in top], page_count=len(by_url), evidence=ev,
               why_it_matters="Traffic reports look healthy while the pages that produce calls get a sliver. Informational queries are also the ones AI Overviews now answer in-SERP, so this traffic is the most exposed to decline.",
               fix="Judge SEO on calls from program/location/admissions pages, not sessions. Keep the blog for E-E-A-T and AI citations, but route it: every post gets a program CTA block, and internal links from top posts to the matching program page.",
               check_first="GSC: clicks by page grouped into blog vs program URLs; GA4/call tracking: calls per landing page group. If blog pages produce under 5% of calls, reallocate content budget to city + program pages.",
               confidence="high")]


def check_commercial_on_home(site, data):
    rows = [_kw(r) for r in _rows(data.get("ranked_organic"))]
    brand_words = {w.lower() for w in (data.get("brand") or "").split() if len(w) > 3}
    city, state = (data.get("city") or "").lower(), (data.get("state") or "").lower()  # "" must not match every keyword
    local = [r for r in rows if re.search(r"rehab|treatment|detox|recovery|iop|outpatient|inpatient|residential", r["keyword"], re.I)
             and not any(b in r["keyword"].lower() for b in brand_words)
             and ((city and city in r["keyword"].lower()) or (state and state in r["keyword"].lower().split()) or "tennessee" in r["keyword"].lower())]
    if not local:
        return []
    home = [r for r in local if urlparse(r["url"]).path in ("", "/")]
    share = len(home) / len(local)
    home_page = next((p for p in html_pages(site) if p.page_type == "home"), None)
    ev = [f"{len(home)} of {len(local)} non-brand local treatment keywords in the top-ranking set are ranked by the homepage, not a program or location page",
          f"Homepage title: '{home_page.title if home_page else '?'}' · H1: {home_page.h1s if home_page else '?'}"]
    ev += [f"'{r['keyword']}' vol {r['volume']}/mo, CPC ${r['cpc']:.0f}, position {r['rank']} -> {r['url'].replace('https://', '')}" for r in sorted(local, key=lambda r: -r['volume'])[:6]]
    if share < 0.6:
        return []
    return [_f(id="os_commercial_on_home", category="content", title="Every commercial '<city> rehab' keyword ranks through the homepage; no program or location page ranks for them",
               severity=4, intent_weight=5, pages=[r["url"] for r in home[:5]], page_count=len(home), evidence=ev,
               why_it_matters="These are the highest-value queries in the market (CPCs near $90 say what a click is worth). A generic homepage caps click-through and sends every intent to one page; competitors rank city + program landing pages with the phone number and program in the title.",
               fix="Rewrite the homepage title/H1 to say what and where ('<Brand> | Alcohol & Drug Rehab in <City>, <ST>'). Build or upgrade one page per city + level of care (detox, residential, IOP) and per location, each with NAP, schema, insurance and FAQ, then internally link them from the homepage hero.",
               check_first="GSC Performance, homepage, queries containing the city: impressions, CTR and position. Compare CTR to the 5-8% typical at position 1-3; the gap is the title problem. Then check which program URLs get impressions for '<city> detox' etc.",
               confidence="high")]


def check_local_pack(site, data):
    host = data["host"]
    ev, pack_hits, pack_total = [], 0, 0
    serps = (data.get("serps") or {}).get("results", [])
    for s in serps:
        if not s.get("ok"):
            continue
        items = s.get("items", [])
        pack = [i for i in items if i.get("type") == "local_pack"]
        if not pack:
            continue
        pack_total += 1
        mine = [i for i in pack if norm_host(i.get("domain") or "") == host]
        pack_hits += bool(mine)
        org = next((i.get("rank") for i in items if i.get("type") == "organic" and norm_host(i.get("domain") or "") == host), None)
        ev.append(f"'{s['keyword']}': 3-pack = {', '.join(norm_host(i['domain']) for i in pack)} -> {'IN pack' if mine else 'NOT in pack'}; organic position {org or 'none'}")
    ratings = []
    link_problems = []
    for kw, m in (data.get("maps") or {}).items():
        res = (m.get("results") if isinstance(m, dict) else None) or []
        if not res:  # error stub or empty Maps response: no evidence either way
            continue
        rows = [_kw({"keyword_data": {}, "ranked_serp_element": {"serp_item": r}}) | {"domain": r.get("domain"), "url": r.get("url") or ""} for r in res]
        mine = [r for r in rows if norm_host(r["domain"] or "") == host]
        top3 = [r for r in rows[:3]]
        ratings += [(r["rating"], r["votes"]) for r in top3 if r["rating"]]
        if mine:
            for r in mine:
                ev.append(f"Google Maps '{kw}' from city centre: {r['title']} at #{r['rank']}, rating {r['rating']} ({r['votes']} reviews)")
                tgt = _strip_utm(r["url"])
                if tgt:
                    try:
                        st = requests.get(tgt, headers={"User-Agent": UA}, timeout=20, allow_redirects=True)
                        if st.status_code != 200 or len(st.history) > 1:
                            link_problems.append(f"GBP website link {tgt} -> HTTP {st.status_code} after {len(st.history)} redirects")
                    except requests.RequestException as e:
                        link_problems.append(f"GBP website link {tgt} -> {e.__class__.__name__}")
        else:
            ev.append(f"Google Maps '{kw}' from city centre: no {host} listing in the top {len(rows)}")
        ev.append(f"  top 3 there: " + "; ".join(f"{r['title']} {r['rating']}★ ({r['votes']})" for r in top3))
    local_rows = [_kw(r) for r in _rows(data.get("ranked_local"))]
    my_ratings = sorted({(r["rating"], r["votes"], r["title"]) for r in local_rows if r["rating"]}, key=lambda x: -(x[1] or 0))
    if my_ratings:
        ev.append("Own GBP listings seen in local packs: " + "; ".join(f"{t} {v}★ ({n})" for v, n, t in my_ratings[:4]))
    comp_avg = sum(r for r, _ in ratings) / len(ratings) if ratings else None
    main_rating = my_ratings[0][0] if my_ratings else None
    gap = (comp_avg - main_rating) if (comp_avg and main_rating) else 0
    if comp_avg and main_rating:
        ev.append(f"Rating gap: main listing {main_rating}★ vs {comp_avg:.1f}★ average for the top-3 Maps results")
    ev += link_problems
    if not ev:
        return []
    sev = 5 if (pack_total and pack_hits / pack_total < 0.5) or gap >= 0.5 or link_problems else 3
    return [_f(id="os_local_pack", category="local", title="Missing from the Google 3-pack for core '<city> rehab' searches; GBP rating trails every competitor in the pack",
               severity=sev, intent_weight=5, pages=[s["keyword"] for s in serps if s.get("ok")][:6], page_count=pack_total, evidence=ev,
               why_it_matters="The 3-pack sits above the #1 organic result on mobile and has a tap-to-call button, so it takes the largest share of calls for '<city> rehab' queries. Rating and review count are the two visible ranking and conversion levers; a 4.0 next to three 4.9s loses the tap even when it appears.",
               fix="A review program (ask at discharge and from alumni, respond to every review, address the 1-star themes); align GBP name, categories, services, hours, photos and phone with the site; link each GBP to its own location page with UTM tags; add Joint Commission and insurance in the GBP description.",
               check_first="GBP Insights per listing: calls, direction requests and website clicks by query; call tracking on the GBP number vs the site number; GSC brand-query trend after review push.",
               confidence="high")]


def check_aio(site, data):
    rows = [_kw(r) for r in _rows(data.get("ranked_aio"))]
    total = (data.get("ranked_aio") or {}).get("totalCount", len(rows))
    serps = (data.get("serps") or {}).get("results", [])
    aio_queries = [s["keyword"] for s in serps if s.get("ok") and any(i.get("type") == "ai_overview" for i in s.get("items", []))]
    if not rows and not aio_queries:
        return []
    by_type = Counter(_page_type(r["url"]) for r in rows)
    money = by_type["home"] + by_type["conversion"] + by_type["local"] + by_type["program"]
    ev = [f"Google AI Overviews cite the domain for {total} keywords; of the top {len(rows)} by volume, {by_type['content'] + by_type['archive']} are blog posts and {money} are program/location/admissions pages",
          "Examples: " + "; ".join(f"'{r['keyword']}' ({r['volume']}/mo) -> {urlparse(r['url']).path}" for r in rows[:4])]
    if aio_queries:
        ev.append(f"AI Overview shown on commercial queries: {', '.join(aio_queries)} (check by hand whether the site is cited there)")
    else:
        ev.append("No AI Overview was shown on the commercial '<city> rehab' queries checked today")
    sev = 3 if money == 0 else 2
    return [_f(id="os_aio_blog_only", category="ai_visibility", title="Google AI Overviews cite the site only for blog posts, never for a program, location or admissions page",
               severity=sev, intent_weight=4, pages=[r["url"] for r in rows[:5]], page_count=len(rows), evidence=ev,
               why_it_matters="AI Overviews and AI Mode are replacing the top organic slot for question-style queries. Being cited for 'what are the 12 steps' earns nothing; being cited for 'how much does rehab cost in <city>' or 'does <brand> take <insurer>' earns calls.",
               fix="Turn program and admissions pages into citable answers: a direct 40-80 word answer under each H2, FAQPage schema, cost/insurance/length-of-stay facts stated plainly, named clinicians, and a comparison page for '<city> rehab options'.",
               check_first="GSC: filter queries starting with 'how', 'does', 'what', 'cost' where the site ranks 4-15; those are the AI Overview candidates. Track brand searches as the AI exposure proxy.",
               confidence="high")]


def check_backlinks(site, data):
    bl = (data.get("backlinks") or {}).get("overview", {}).get("overview", {})
    summ = bl.get("summary", {})
    trends = bl.get("trends", [])
    if not summ:
        return []
    first, last = (trends[0], trends[-1]) if len(trends) >= 2 else (None, None)
    ev = [f"Referring domains {summ.get('referringDomains')}, backlinks {summ.get('backlinks')}, domain rank {summ.get('rank')}, spam score {summ.get('targetSpamScore')}"]
    decline = 0
    if first and last:
        decline = (first["backlinks"] - last["backlinks"]) / max(first["backlinks"], 1)
        ev.append(f"12-month trend: backlinks {first['backlinks']} -> {last['backlinks']} ({-decline:+.0%}), referring domains {first['referringDomains']} -> {last['referringDomains']}")
    top = (data.get("backlinks") or {}).get("referringDomains", {}).get("rows", [])[:5]
    ev += [f"Top referrer: {r['domain']} ({r['backlinks']} links, spam {r['spamScore']})" for r in top]
    if decline < 0.05 and (summ.get("targetSpamScore") or 0) < 30:
        return []
    return [_f(id="os_backlinks", category="trust", title="Link profile is shrinking and leans on low-quality rehab directories",
               severity=2, intent_weight=3, pages=[], page_count=len(top), evidence=ev,
               why_it_matters="Authority decides who wins the organic #1 for '<city> rehab' once titles and pages are fixed; a decaying profile with directory-heavy links is a slow leak, not an emergency.",
               fix="Earn links where families and referrers already are: local news, hospital systems, university partnerships, state/county resources, alumni stories; disavow nothing yet, audit the 'rehab*.us' style directories.",
               check_first="GSC Links report: top linking sites and the pages they link to; watch whether referring domains keep dropping month over month.",
               confidence="medium")]


ALL_OPENSEO_CHECKS = [check_intent_mix, check_commercial_on_home, check_local_pack, check_aio, check_backlinks]


def write_market_summary(data, out_dir):
    ov = data.get("overview") or {}
    bl = ((data.get("backlinks") or {}).get("overview", {}).get("overview", {}) or {}).get("summary", {})
    L = [f"# Market data for {data['host']} (OpenSEO / DataForSEO)\n",
         f"Estimated organic traffic: {ov.get('organicTraffic')} visits/mo · ranking keywords: {ov.get('organicKeywords')} · "
         f"referring domains: {bl.get('referringDomains')} · domain rank: {bl.get('rank')}\n"]
    comps = (data.get("competitors") or {}).get("competitors") or []
    if comps:
        L.append("## Who wins the local SERPs (visibility across the query set)\n")
        L.append("| Domain | Visibility | Avg pos | Est. traffic |")
        L.append("|---|---|---|---|")
        L += [f"| {c.get('domain')} | {c.get('visibility') or 0:.2f} | {c.get('avg_position') or 0:.1f} | {c.get('etv') or 0:.0f} |" for c in comps[:12]]
    serps = (data.get("serps") or {}).get("results", [])
    if serps:
        L.append("\n## Live SERPs\n")
        for s in serps:
            if not s.get("ok"):
                continue
            L.append(f"### {s['keyword']}")
            for i in s.get("items", [])[:10]:
                if i.get("type") in ("local_pack", "organic", "ai_overview", "knowledge_graph"):
                    L.append(f"- {i['type']} #{i.get('rank')}: {i.get('domain') or ''} {('— ' + (i.get('title') or ''))[:90]}")
    with open(os.path.join(out_dir, "market.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")
