"""Topical authority of the audited site vs local competitors, from ranked-keyword data (OpenSEO / DataForSEO).

run(site, market, out_dir, client=None) -> list[Finding]. Pulls each domain's top organic keywords twice (sorted by
traffic and by volume), buckets them into addiction-treatment topic clusters by regex, scores share-of-topic
(domain's top-10 keyword count / best domain's * 100), lists keyword gaps (2+ competitors in the top 20, audited site
absent from its cached sets) and writes topical_authority.md/.json. With client=None it reads only cached JSON under
out_dir/openseo. Never raises."""
import json
import logging
import os
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from .checks import _f
from .openseo import _cached

log = logging.getLogger("audit")
COMPETITORS = ["recoveryranch.com", "southeastaddictiontn.com", "nashvilleaddictionrecovery.com", "liveagaindetox.com", "apex.rehab", "recoveryunplugged.com"]
BRAND_TOKENS = ["cumberland", "recovery ranch", "southeast addiction", "nashville addiction recovery", "live again", "apex", "recovery unplugged"]
TOPICS = [  # key, label, regex (word-bounded, case-insensitive); a keyword can sit in several topics
    ("alcohol", "Alcohol", r"alcohol\w*|drinking|drunk|binge|liquor|beer|wine|hangover|delirium tremens"), ("opioids",
     "Opioids / fentanyl / heroin", r"opioids?|opiates?|fentanyl|heroin|oxy\w*|percocet|hydrocodone|suboxone|methadone|kratom|vicodin|morphine|tramadol|naloxone|narcan|painkillers?"),
    ("stimulants", "Stimulants (meth, cocaine, adderall)", r"meth|methamphetamine|cocaine|crack|adderall|amphetamines?|stimulants?|ritalin|vyvanse"),
    ("benzos", "Benzos / barbiturates / sedatives", r"benzo\w*|xanax|valium|klonopin|ativan|barbiturates?|sedatives?|ambien|alprazolam|gabapentin"),
    ("cannabis", "Cannabis", r"cannabis|marijuana|weed|thc|delta ?8|cbd"), ("detox", "Detox", r"detox\w*|withdrawals?|paws|post[- ]acute"),
    ("residential", "Residential / inpatient", r"residential|inpatient|in-patient|long[- ]term|28[- ]day|30[- ]day|90[- ]day"),
    ("outpatient", "Outpatient / IOP / PHP", r"outpatient|iop|php|partial hospitali\w*|day program"), ("mental",
     "Mental health & dual diagnosis", r"mental|anxiety|depress\w*|bipolar|trauma\w*|ptsd|mania|manic|dual diagnosis|co-?occurring|schizo\w*|ocd|adhd|psychiatr\w*|eating disorders?|dysthymia|mood|stress|emdr|dbt|cbt"),
    ("twelve", "12-step & recovery education", r"12[- ]?steps?|twelve steps?|aa|aas|a a|na|alcoholics anonymous|narcotics anonymous|sober\w*|sobriety|relapse\w*|sponsors?|serenity prayer|big book|recovery (?:quotes|prayers?)"),
    ("insurance", "Insurance & cost", r"insurance|aetna|bcbs|blue cross|cigna|united ?healthcare|humana|cost|costs|price|prices|pricing|free|medicaid|medicare|tricare|tenncare|afford\w*"),
    ("family", "Family & loved ones", r"family|families|spouse|husband|wife|son|daughter|parents?|intervention\w*|loved ones?|codependen\w*|enabl\w*|al-?anon"),
    ("youth", "Adolescents & young adults", r"teens?|teenagers?|adolescents?|young adults?|college|youth|students?"),
    ("pros", "Professionals & veterans", r"professionals?|executives?|veterans?|military|first responders?|nurses?|doctors?|pilots?|lawyers?|attorneys?|physicians?"),
    ("local", "Local intent", r"nashville|tennessee|tn|memphis|knoxville|chattanooga|near me|close to me|franklin|murfreesboro|clarksville|brentwood|kingston springs|cookeville"),
]
LABEL = {k: lab for k, lab, _ in TOPICS} | {"brand": "Brand", "other": "Other"}
RX = {k: re.compile(r"\b(?:" + p + r")\b", re.I) for k, _, p in TOPICS}
BRAND_RX = re.compile(r"\b(?:" + "|".join(map(re.escape, BRAND_TOKENS)) + r")\b", re.I)
KEYS = [k for k, _, _ in TOPICS] + ["brand", "other"]
COMMERCIAL = {"detox", "residential", "outpatient", "insurance", "local"}
PRIMARY = ["local", "insurance", "detox", "residential", "outpatient", "opioids", "alcohol", "stimulants", "benzos",
           "cannabis", "youth", "pros", "family", "mental", "twelve"]
COMMERCIAL_RX = re.compile(r"\brehabs?\b|\btreatment (?:centers?|facilit\w*|programs?)\b|\baddiction (?:centers?|treatment)\b")

def _host(u):
    h = (urlparse(u if "//" in (u or "") else "//" + (u or "")).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h

def _load(out_dir, name, client, fn):
    path = os.path.join(out_dir, "openseo", f"{name}.json")
    if os.path.exists(path):
        try:
            with open(path) as fh:
                d = json.load(fh)
            return d if client is None or not (isinstance(d, dict) and d.get("error")) else _cached(out_dir, name, False, fn)
        except Exception:
            pass
    return _cached(out_dir, name, False, fn) if client is not None else {}

def _topics(kw):
    t = [k for k in RX if RX[k].search(kw)]
    return t + ["brand"] if BRAND_RX.search(kw) else (t or ["other"])

def _primary(kw, tps):
    return "brand" if "brand" in tps else next((k for k in PRIMARY if k in tps), "other")

def _bucket(kw, tps):
    return "brand" if "brand" in tps else "commercial/local" if set(tps) & COMMERCIAL or COMMERCIAL_RX.search(kw) else "informational"

def _rows(*datasets):
    best = {}
    for d in datasets:
        for k in (d.get("keywords") or []) if isinstance(d, dict) else []:
            kd = k.get("keyword_data") or {}
            it = (k.get("ranked_serp_element") or {}).get("serp_item") or {}
            kw = (kd.get("keyword") or "").lower().strip()
            if not kw:
                continue
            r = {"kw": kw, "vol": (kd.get("keyword_info") or {}).get("search_volume") or 0,
                 "rank": it.get("rank_group") or 999, "url": it.get("url") or "", "etv": float(it.get("etv") or 0),
                 "intent": (kd.get("search_intent_info") or {}).get("main_intent") or ""}
            best[kw] = r if kw not in best or r["rank"] < best[kw]["rank"] else best[kw]
    for r in best.values():
        r["topics"] = t = _topics(r["kw"]); r["primary"], r["bucket"] = _primary(r["kw"], t), _bucket(r["kw"], t)
    return list(best.values())

def _stats(rows):
    st = {t: {"keywords": 0, "volume": 0, "etv": 0.0, "top3": 0, "top10": 0, "urls": set()} for t in KEYS}
    for r in rows:
        for t in r["topics"]:
            s = st[t]
            s["keywords"] += 1; s["volume"] += r["vol"]; s["etv"] += r["etv"]
            s["top3"] += r["rank"] <= 3; s["top10"] += r["rank"] <= 10; s["urls"].add(r["url"])
    return {t: dict(v, urls=len(v["urls"]), etv=round(v["etv"], 1)) for t, v in st.items()}

def _fetch(host, comps, out_dir, client):
    jobs = {"domain_overview": ("get_domain_overview", {"domain": host}), "ranked_keywords_organic": ("get_ranked_keywords", {"target": host, "sortBy": "traffic_estimate"}),
            "ranked_keywords_organic_volume": ("get_ranked_keywords", {"target": host, "sortBy": "search_volume"})}
    for d in comps:
        jobs[f"ranked_{d}_traffic"] = ("get_ranked_keywords", {"target": d, "sortBy": "traffic_estimate"})
        jobs[f"ranked_{d}_volume"] = ("get_ranked_keywords", {"target": d, "sortBy": "search_volume"})
        jobs[f"overview_{d}"] = ("get_domain_overview", {"domain": d})
    for args in (a for t, a in jobs.values() if t == "get_ranked_keywords"):
        args.update(limit=100, resultTypes=["organic"])
    with ThreadPoolExecutor(6) as ex:
        futs = {n: ex.submit(_load, out_dir, n, client, (lambda t=t, a=a: client.call(t, a))) for n, (t, a) in jobs.items()}
        return {n: f.result() for n, f in futs.items()}

def _compute(host, comps, data):
    doms = [host] + comps
    rows = {host: _rows(data.get("ranked_keywords_organic"), data.get("ranked_keywords_organic_volume"))}
    for d in comps:
        rows[d] = _rows(data.get(f"ranked_{d}_traffic"), data.get(f"ranked_{d}_volume"))
    stats = {d: _stats(rows[d]) for d in doms}
    score, best = {d: {} for d in doms}, {}
    for t in KEYS:
        mx = max(stats[d][t]["top10"] for d in doms)
        for d in doms:
            score[d][t] = round(100 * stats[d][t]["top10"] / mx) if mx else 0
        best[t] = max(comps, key=lambda d: (stats[d][t]["top10"], stats[d][t]["etv"])) if comps else ""
    core = [t for t in KEYS if t not in ("brand", "other")]
    rel = {t: (score[host][t], score[host][t] - (score[best[t]][t] if best[t] else 0)) for t in core}
    strongest = sorted(core, key=lambda t: (-rel[t][0], -rel[t][1]))[:3]
    gap10 = {t: (stats[best[t]][t]["top10"] if best[t] else 0) - stats[host][t]["top10"] for t in core}
    weakest = sorted([t for t in core if gap10[t] > 0], key=lambda t: (-gap10[t], rel[t][0]))[:3]
    mine, cand, gaps = {r["kw"] for r in rows[host]}, defaultdict(list), []
    for d in comps:
        for r in rows[d]:
            if r["rank"] <= 20 and r["vol"] >= 100 and r["kw"] not in mine and not BRAND_RX.search(r["kw"]):
                cand[r["kw"]].append((d, r))
    for kw, hits in cand.items():
        if len({d for d, _ in hits}) >= 2 and (bst := min(hits, key=lambda x: (x[1]["rank"], -x[1]["etv"]))):
            d, r = bst
            gaps.append({"keyword": kw, "volume": r["vol"], "topic": r["primary"], "best_competitor": d,
                         "rank": r["rank"], "url": r["url"], "competitors": sorted({x for x, _ in hits})})
    gaps = sorted(gaps, key=lambda g: -g["volume"])[:40]
    mix = {}
    for d in doms:
        tot = sum(r["etv"] for r in rows[d]) or 1.0
        b = Counter()
        for r in rows[d]:
            b[r["bucket"]] += r["etv"]; b["dfs_" + (r["intent"] or "unknown")] += r["etv"]
        ov = data.get("domain_overview" if d == host else f"overview_{d}") or {}
        mix[d] = {"etv": round(sum(r["etv"] for r in rows[d]), 1), "organic_traffic": ov.get("organicTraffic"),
                  "organic_keywords": ov.get("organicKeywords"),
                  **{k: round(100 * v / tot, 1) for k, v in b.items()}}
    return {"host": host, "competitors": comps, "topics": {k: LABEL[k] for k in KEYS},
            "regex": {k: p for k, _, p in TOPICS} | {"brand": BRAND_TOKENS}, "stats": stats, "score": score,
            "best_competitor": best, "strongest": strongest, "weakest": weakest, "gaps": gaps, "intent_mix": mix,
            "keywords_sampled": {d: len(rows[d]) for d in doms},
            "overviews": {d: data.get(f"overview_{d}") for d in comps}}

def _bullets(R):
    h, s, sc, b, mix = R["host"], R["stats"], R["score"], R["best_competitor"], R["intent_mix"]
    out = []
    for t in ("local", "detox"):
        o = max([h] + R["competitors"], key=lambda d: (s[d][t]["top10"], s[d][t]["etv"]))
        out.append(f"**{LABEL[t]}** is owned by {o} ({s[o][t]['top10']} top-10 keywords, ~{s[o][t]['etv']:,.0f} visits/mo); "
                   f"{h} scores {sc[h][t]}/100 with {s[h][t]['top10']} top-10 keywords.")
    edu = sum(s[h][t]["etv"] for t in ("twelve", "mental")) / (mix[h]["etv"] or 1) * 100
    comp_info = [mix[d].get("informational", 0) for d in R["competitors"]]
    out.append(f"{h}'s authority is concentrated in recovery education: 12-step + mental-health topics carry {edu:.0f}% of its "
               f"sampled traffic and {mix[h].get('informational', 0):.0f}% is informational vs a competitor median of "
               f"{sorted(comp_info)[len(comp_info) // 2] if comp_info else 0:.0f}%.")
    out.append(f"Strongest topics: {', '.join(f'{LABEL[t]} ({sc[h][t]})' for t in R['strongest'])}; weakest relative to "
               f"the best competitor: {', '.join(f'{LABEL[t]} ({sc[h][t]} vs {b[t]} {sc[b[t]][t]})' for t in R['weakest'])}.")
    g = R["gaps"]
    tc = Counter(x["topic"] for x in g)
    out.append(f"{len(g)} gap keywords ({sum(x['volume'] for x in g):,} searches/mo) rank top 20 for 2+ competitors but not "
               f"for {h}; most fall in {', '.join(f'{LABEL[t]} ({n})' for t, n in tc.most_common(3))}.")
    return out

def _write_md(R, path):
    h, doms, s, sc = R["host"], [R["host"]] + R["competitors"], R["stats"], R["score"]
    L = [f"# Topical authority: {h} vs competitors", "",
         "Source: OpenSEO `get_ranked_keywords` (organic, top 100 by traffic + top 100 by volume per domain, merged). "
         "Score = domain's top-10 keyword count in the topic / best domain's * 100. Keywords can belong to several topics.",
         "", "## Topical authority matrix (0-100)", "", "| Topic | " + " | ".join(doms) + " | Best competitor |",
         "|---|" + "---|" * (len(doms) + 1)]
    for t in KEYS:
        L.append(f"| {LABEL[t]} | " + " | ".join(f"{sc[d][t]} ({s[d][t]['top10']})" for d in doms) + f" | {R['best_competitor'][t]} |")
    L += ["", "Cell = score (top-10 keyword count).", "", f"## {h}: strongest and weakest topics", "",
          "| | Topic | Score | KW | Top 3 | Top 10 | Volume | ETV | URLs | Best competitor (score) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for tag, ts in (("Strongest", R["strongest"]), ("Weakest", R["weakest"])):
        for t in ts:
            x, bc = s[h][t], R["best_competitor"][t]
            L.append(f"| {tag} | {LABEL[t]} | {sc[h][t]} | {x['keywords']} | {x['top3']} | {x['top10']} | {x['volume']:,} | "
                     f"{x['etv']:,.0f} | {x['urls']} | {bc} ({sc[bc][t] if bc else 0}) |")
    L += ["", "## Keyword gap (volume >= 100, 2+ competitors top 20, absent from audited site's cached sets)", "",
          "| Keyword | Volume | Topic | Best competitor | Rank | URL | Also ranking |", "|---|---|---|---|---|---|---|"]
    for g in sorted(R["gaps"], key=lambda g: (g["topic"], -g["volume"])):
        L.append(f"| {g['keyword']} | {g['volume']:,} | {LABEL[g['topic']]} | {g['best_competitor']} | {g['rank']} | {g['url']} | "
                 f"{', '.join(c for c in g['competitors'] if c != g['best_competitor'])} |")
    L += ["", "## Intent mix (share of sampled estimated traffic)", "",
          "| Domain | Sampled ETV | Organic traffic / kws (overview) | Commercial/local % | Informational % | Brand % | DFS informational % | DFS commercial+transactional % |",
          "|---|---|---|---|---|---|---|---|"]
    for d in doms:
        m = R["intent_mix"][d]
        L.append(f"| {d} | {m['etv']:,.0f} | {m.get('organic_traffic') or 0:,} / {m.get('organic_keywords') or 0:,} | {m.get('commercial/local', 0)} | "
                 f"{m.get('informational', 0)} | {m.get('brand', 0)} | {m.get('dfs_informational', 0)} | "
                 f"{round(m.get('dfs_commercial', 0) + m.get('dfs_transactional', 0), 1)} |")
    L += ["", "## Takeaways", ""] + [f"- {b}" for b in _bullets(R)]
    L += ["", "## Topic cluster definitions (regex, word-bounded, case-insensitive)", ""]
    L += [f"- **{LABEL[k]}**: `{p}`" for k, _, p in TOPICS]
    L += [f"- **Brand**: any of {', '.join(BRAND_TOKENS)}", "- **Other**: no topic matched",
          "", "Commercial/local bucket = detox, residential, outpatient, insurance or local topics, or 'rehab'/'treatment center'; "
          "brand = brand token; everything else informational. Gap list caveat: the audited site has thousands of ranked "
          "keywords and only ~200 are cached, so verify each gap in GSC before building."]
    with open(path, "w") as fh:
        fh.write("\n".join(L) + "\n")

def _findings(R, market):
    h, s, sc, b, g = R["host"], R["stats"], R["score"], R["best_competitor"], R["gaps"]
    city = (market or {}).get("city") or "Nashville"
    ev = [f"Weak: {LABEL[t]} - {h} {sc[h][t]}/100 ({s[h][t]['top10']} top-10 kws) vs {b[t]} {sc[b[t]][t]} ({s[b[t]][t]['top10']})" for t in R["weakest"]]
    ev += [f"Strong: {LABEL[t]} - {h} {sc[h][t]}/100 ({s[h][t]['top10']} top-10 kws, ~{s[h][t]['etv']:,.0f} visits/mo)" for t in R["strongest"]]
    m = R["intent_mix"][h]
    ev.append(f"Intent mix of {h}'s sampled traffic: {m.get('informational', 0)}% informational, {m.get('commercial/local', 0)}% commercial/local, {m.get('brand', 0)}% brand")
    why = (f"Google ranks city and program pages ('{city} detox', 'inpatient rehab {city}', IOP pages) partly on the depth of the "
           f"topic cluster behind them. Competitors with denser clusters in {', '.join(LABEL[t] for t in R['weakest'])} win the "
           "commercial queries that become admissions, while recovery-education traffic rarely converts.")
    hubs = defaultdict(list)
    for x in g:
        hubs[x["topic"]].append(x["keyword"])
    fix = ("Build topic hubs (one pillar program/city page plus 4-8 supporting articles, interlinked) for: " +
           "; ".join(f"{LABEL[t]} -> target {', '.join(repr(k) for k in kws[:5])}" for t, kws in
                     sorted(hubs.items(), key=lambda kv: -sum(x['volume'] for x in g if x['topic'] == kv[0]))[:5]) +
           ". Link each hub from the matching program page and the city page; reuse the strong 12-step/education pages as internal-link sources.")
    check = ("GSC > Performance > Search results, Queries filtered by regex per cluster (e.g. 'detox|withdrawal', "
             f"'{city.lower()}|tennessee|near me', 'insurance|cost|aetna|cigna', 'outpatient|iop|php'): confirm impressions and "
             "average position for the gap keywords first; a page already sitting at 11-40 needs consolidation, not a new URL.")
    out = [_f(id="topical_authority_matrix", category="content", severity=3, intent_weight=4, pages=[], page_count=0,
              title=f"Topical authority trails competitors on {', '.join(LABEL[t] for t in R['weakest'])}",
              evidence=ev, why_it_matters=why, fix=fix, check_first=check, confidence="medium")] if R["weakest"] else []
    if g:
        vol = sum(x["volume"] for x in g)
        out.append(_f(id="keyword_gap_competitors", category="content", severity=4 if vol >= 20000 else 3, intent_weight=4,
                      pages=[], page_count=0, title=f"{len(g)} keywords ({vol:,} searches/mo) rank top 20 for 2+ "
                      f"competitors but not for {h}",
                      evidence=[f"{x['keyword']} ({x['volume']:,}/mo, {LABEL[x['topic']]}) - {x['best_competitor']} #{x['rank']} {x['url']}"
                                for x in g[:12]], why_it_matters=why, fix=fix, check_first=check, confidence="medium"))
    return out

def run(site: dict, market: dict | None, out_dir: str, client=None) -> list:
    try:
        host = _host((site or {}).get("host") or (site or {}).get("start_url") or "")
        comps = [_host(c) for c in ((market or {}).get("topical_competitors") or COMPETITORS) if _host(c) != host]
        data = _fetch(host, comps, out_dir, client)
        comps = [d for d in comps if (data.get(f"ranked_{d}_traffic") or {}).get("keywords")]
        R = _compute(host, comps, data)
        with open(os.path.join(out_dir, "topical_authority.json"), "w") as fh:
            json.dump(R, fh, indent=1, default=list)
        _write_md(R, os.path.join(out_dir, "topical_authority.md"))
        return _findings(R, market) if comps else []
    except Exception as e:
        log.warning("topical_authority failed: %s", e)
        return []
