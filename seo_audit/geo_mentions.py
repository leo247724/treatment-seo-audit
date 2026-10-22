"""AI-answer share of voice from <out_dir>/geo_mentions.json (Perplexity answers to brand and non-brand queries)."""
import json
import logging
import os
from collections import Counter
from urllib.parse import urlparse

from .models import Finding
from .checks import _f

log = logging.getLogger("audit")


def _host(u) -> str:
    u = (u or "").strip().lower()
    h = (urlparse(u).netloc if "//" in u else u.split("/")[0]).split(":")[0]
    return h[4:] if h.startswith("www.") else h


def _same(a, b) -> bool:
    a, b = _host(a), _host(b)
    return bool(a and b) and (a == b or a.endswith("." + b) or b.endswith("." + a))


def _split(data):
    qs = [q for q in (data.get("queries") or []) if isinstance(q, dict)]
    return [q for q in qs if q.get("type") == "non-brand"], [q for q in qs if q.get("type") == "brand"]


def _audited(data, host):
    brands = [b for b in (data.get("brands") or []) if b.get("name")]
    return next((b for b in brands if _same(b.get("domain"), host)), brands[0] if brands else None)


def _cited(q, brand) -> bool:
    s = (q.get("brands") or {}).get(brand["name"]) or {}
    return bool(s.get("cited")) or any(_same(u, brand.get("domain")) for u in q.get("citations") or [])


def share_of_voice(data) -> dict:
    """{brand: {mentions, citations, mean_pos, m, c, n}} over non-brand queries."""
    nb, _ = _split(data)
    n, out = len(nb), {}
    for b in [b for b in data.get("brands") or [] if b.get("name")]:
        st = [(q.get("brands") or {}).get(b["name"]) or {} for q in nb]
        m = sum(bool(s.get("mentioned_in_answer")) for s in st)
        c = sum(_cited(q, b) for q in nb)
        pos = [s["position_of_first_mention"] for s in st if isinstance(s.get("position_of_first_mention"), (int, float))]
        out[b["name"]] = {"mentions": m / n if n else 0.0, "citations": c / n if n else 0.0,
                          "mean_pos": sum(pos) / len(pos) if pos else None, "m": m, "c": c, "n": n}
    return out


def _rank(sov, name, key):
    v = sov[name][key]
    if key == "mean_pos":
        return 1 + sum(1 for o in sov.values() if o[key] is not None and (v is None or o[key] < v))
    return 1 + sum(1 for o in sov.values() if o[key] > v)


def share_of_voice_table(data, host=None) -> str:
    data = _normalize(data)
    """Markdown table of AI-answer share of voice across non-brand queries; audited brand in bold."""
    try:
        sov = share_of_voice(data)
        if not sov:
            return ""
        me = (_audited(data, host) or {}).get("name") if host else None
        rows = ["| Brand | Mentioned in answer | Cited | Mean first-mention position |", "|---|---|---|---|"]
        for name, s in sorted(sov.items(), key=lambda kv: (-kv[1]["mentions"], -kv[1]["citations"])):
            pos = f"{s['mean_pos']:.1f}" if s["mean_pos"] is not None else "-"
            rows.append(f"| {f'**{name}**' if name == me else name} | {s['m']}/{s['n']} ({s['mentions']:.0%}) | "
                        f"{s['c']}/{s['n']} ({s['citations']:.0%}) | {pos} |")
        return "\n".join(rows)
    except Exception as e:  # never break the report
        log.warning("geo_mentions: share_of_voice_table failed: %s", e)
        return ""


def _third_party(qs, brands, exclude=()):
    cnt, skip = Counter(), [b.get("domain") for b in brands] + list(exclude)
    for q in qs:
        doms = q["third_party_cited"] if q.get("third_party_cited") is not None else q.get("citations") or []
        cnt.update(d for d in {_host(d) for d in doms if d} if not any(_same(d, x) for x in skip))
    return cnt


WHY = ("Families searching for treatment increasingly ask an AI assistant which centers to call, and they phone the "
       "names it gives and the sites it links. A center that is not named or cited in those answers never gets the "
       "call; the directories cited instead route callers to paid listings and competitors.")
CHECK = ("GSC Performance filtered to brand queries (16-month impressions/clicks trend) to see whether AI exposure is "
         "already moving branded demand, and add a 'How did you hear about us?' tag in call tracking with an "
         "'AI assistant (ChatGPT/Perplexity)' option so AI-sourced calls are counted before and after the fix.")


def run(site: dict, market: dict | None, out_dir: str, client=None) -> list[Finding]:
    try:
        path = os.path.join(out_dir, "geo_mentions.json")
        if not os.path.exists(path):
            log.warning("geo_mentions: %s not found, skipping AI share-of-voice check", path)
            return []
        with open(path, encoding="utf-8") as fh:
            data = _normalize(json.load(fh))
        findings = _findings(site or {}, data)
        try:
            _write_md(site or {}, data, out_dir)
        except Exception as e:
            log.warning("geo_mentions: could not write geo_mentions.md: %s", e)
        return findings
    except Exception as e:
        log.warning("geo_mentions: check failed: %s", e)
        return []


def _normalize(data):
    """Accept both dataset shapes: brands with `domain` or `domains[]`; per-query `brands` dict or `brand_mentions` list."""
    for b in data.get("brands") or []:
        if not b.get("domain") and b.get("domains"):
            b["domain"] = b["domains"][0]
    for q in data.get("queries") or []:
        if not q.get("brands") and isinstance(q.get("brand_mentions"), list):
            q["brands"] = {m.get("brand") or m.get("name"): {"mentioned_in_answer": bool(m.get("mentioned_in_answer", m.get("mentioned"))),
                                                           "cited": bool(m.get("cited")),
                                                           "position_of_first_mention": m.get("position_of_first_mention")}
                           for m in q["brand_mentions"] if (m.get("brand") or m.get("name"))}
        if not q.get("third_party_cited") and q.get("directory_domains_cited"):
            q["third_party_cited"] = q["directory_domains_cited"]
    return data


def _write_md(site, data, out_dir):
    """geo_mentions.md: share-of-voice table, per-query citations, absent queries, most-cited third parties."""
    host = site.get("host", "")
    me = _audited(data, host)
    nb, bq = _split(data)
    brands = data.get("brands") or []
    L = [f"# AI answer share of voice: {host}\n",
         f"Engine: {data.get('engine', '?')} · run {data.get('run_date', '?')} · {len(nb)} non-brand queries, {len(bq)} brand queries. "
         "Mentioned = brand named in the answer text; cited = the brand's own domain among the answer's sources.\n",
         "## Share of voice (non-brand queries)\n", share_of_voice_table(data, host) or "_no data_", ""]
    if me:
        absent = [q.get("query", "") for q in nb if not ((q.get("brands") or {}).get(me["name"]) or {}).get("mentioned_in_answer") and not _cited(q, me)]
        L += [f"## Queries where {me['name']} is absent ({len(absent)} of {len(nb)})\n"] + [f"- {q}" for q in absent] + [""]
    tp = _third_party(nb, brands).most_common(10)
    L += ["## Most-cited third-party domains (non-brand queries)\n", "| Domain | Answers citing it |", "|---|---|"] + [f"| {d} | {k} |" for d, k in tp] + [""]
    L += ["## Per query\n", "| Type | Query | Brands mentioned | Domains cited |", "|---|---|---|---|"]
    for q in (nb + bq):
        mentioned = [b for b, v in (q.get("brands") or {}).items() if (v or {}).get("mentioned_in_answer")]
        hosts = sorted({_host(u) for u in q.get("citations") or []})
        L.append(f"| {q.get('type', '')} | {q.get('query', '')} | {', '.join(mentioned) or 'none'} | {', '.join(hosts[:8])} |")
    with open(os.path.join(out_dir, "geo_mentions.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def _findings(site, data) -> list[Finding]:
    me = _audited(data, site.get("host", ""))
    nb, bq = _split(data)
    if not me or not (nb or bq):
        log.warning("geo_mentions: no brands or queries in geo_mentions.json")
        return []
    brands, name, dom = data.get("brands") or [], me["name"], me.get("domain", "")
    engine, when = data.get("engine", "perplexity").title(), data.get("run_date", "")
    tp = _third_party(nb, brands).most_common(5)
    fix = ("Publish answer-ready pages that answer the absent queries in the first two or three sentences (levels of care, "
           "insurance, cost, length of stay, location); add Organization/MedicalOrganization entity schema with sameAs links "
           f"to every directory profile; claim and complete listings on the directories AI cites ({', '.join(d for d, _ in tp[:3]) or 'see evidence'}); "
           "publish an outcomes page (accreditation, completion and alumni follow-up data) that answers can quote.")
    out = []
    if nb:
        sov = share_of_voice(data)
        s, n = sov[name], len(nb)
        r_m, r_c, r_p = _rank(sov, name, "mentions"), _rank(sov, name, "citations"), _rank(sov, name, "mean_pos")
        ranked = sorted(sov.items(), key=lambda kv: (-kv[1]["mentions"], -kv[1]["citations"]))
        ahead = [b for b, o in ranked if o["mentions"] > s["mentions"]]
        ahead_c = [b for b, o in ranked if o["citations"] > s["citations"]]
        absent = [q.get("query", "") for q in nb if not ((q.get("brands") or {}).get(name) or {}).get("mentioned_in_answer") and not _cited(q, me)]
        weak = s["citations"] < 0.5 or r_m > 3
        pos = f"{s['mean_pos']:.1f}" if s["mean_pos"] is not None else "never mentioned"
        board = "; ".join(f"{b} {o['mentions']:.0%}/{o['citations']:.0%}" for b, o in ranked)
        own = sorted({u for q in nb for u in q.get("citations") or [] if _same(u, dom)})
        out.append(_f(
            id="ai_share_of_voice", category="ai_visibility", severity=4 if weak else 2, intent_weight=5,
            title=(f"{name} trails competitors in AI answers for treatment searches" if weak
                   else f"{name} holds a top-3 share of AI answers for treatment searches"),
            pages=own[:5], page_count=max(len(absent), 1),
            evidence=[f"{engine} run {when}: {n} non-brand queries, {len(bq)} brand queries",
                      f"{name}: mentioned in {s['m']}/{n} ({s['mentions']:.0%}), cited from {dom} in {s['c']}/{n} ({s['citations']:.0%}), mean first-mention position {pos}",
                      f"Rank among {len(sov)} brands: #{r_m} mentions, #{r_c} citations, #{r_p} first-mention position",
                      f"Brands ahead on mentions: {', '.join(ahead) or 'none'}; on citations: {', '.join(ahead_c) or 'none'}",
                      f"Share of voice (mentioned/cited): {board}",
                      f"Absent from {len(absent)}/{n} answers" + (": " + "; ".join(f'"{q}"' for q in absent[:5]) if absent else ""),
                      f"Most-cited third-party domains: {', '.join(f'{d} ({k})' for d, k in tp) or 'none'}"],
            why_it_matters=WHY, fix=fix, check_first=CHECK, confidence="medium" if n >= 5 else "low"))
    if bq:
        own_hits = sum(_cited(q, me) for q in bq)
        low = own_hits < len(bq) / 2
        others = _third_party(bq, [me], exclude=[dom]).most_common(5)
        out.append(_f(
            id="ai_brand_answer_sources", category="ai_visibility", intent_weight=5,
            severity=4 if low else 2, title=(f"AI answers about {name} are sourced mostly from other sites" if low
                                             else f"AI answers about {name} cite {dom}"),
            pages=sorted({u for q in bq for u in q.get("citations") or [] if _same(u, dom)})[:5], page_count=len(bq),
            evidence=[f"{dom} cited in {own_hits}/{len(bq)} brand-query answers ({own_hits / len(bq):.0%})",
                      f"Other domains shaping the brand answer: {', '.join(f'{d} ({k})' for d, k in others) or 'none'}"],
            why_it_matters=WHY, fix=fix, check_first=CHECK, confidence="medium"))
    return out
