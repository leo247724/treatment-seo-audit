"""Backlink authority audit: the site's DataForSEO link profile vs the local SERP competitors (via OpenSEO).

run(site, market, out_dir, client=None) -> list[Finding]. With client=None it reads only cached JSON under
<out_dir>/openseo/. It never raises; failures are logged and yield fewer findings."""
import json
import logging
import os
import re
from urllib.parse import urlparse

from .checks import _f
from .openseo import _cached

log = logging.getLogger("audit")

# Top local competitors from serp_competitors.json (chosen for the Nashville market); market["competitors"] overrides.
DEFAULT_COMPETITORS = ["southeastaddictiontn.com", "nashvilleaddictionrecovery.com", "liveagaindetox.com",
                       "recoveryranch.com", "thenextdoorrecovery.org"]
DIRECTORY_RE = re.compile(r"rehab|addiction|recovery|detox|treatment|directory|listing", re.I)
SPAM_CUTOFF = 30
CHECK_FIRST = ("Search Console > Links report: 'Top linking sites' and 'Top linked pages' (export both); compare the "
               "linking-site count with the DataForSEO numbers here and note which pages the links actually point at.")


def _host(u):
    h = (urlparse(u if "//" in (u or "") else "//" + (u or "")).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def _load(out_dir, name, client, fn, quiet=False):
    """Cached JSON when present; live call only when a client is given (never writes error stubs offline)."""
    path = os.path.join(out_dir, "openseo", f"{name}.json")
    if client is None:
        if not os.path.exists(path):
            if not quiet:
                log.warning("backlinks: no cached %s and no client", path)
            return None
        try:
            with open(path) as fh:
                return json.load(fh)
        except (OSError, ValueError) as e:
            log.warning("backlinks: unreadable cache %s: %s", path, e)
            return None
    return _cached(out_dir, name, True, fn)


def _summary(d):
    ov = ((d or {}).get("overview") or {}).get("overview") or {}
    return ov.get("summary") or {}, ov.get("trends") or [], ov.get("newLostTrends") or [], \
        ((d or {}).get("referringDomains") or {}).get("rows") or []


def _collect(site, market, out_dir, client):
    host = _host((site or {}).get("start_url") or (site or {}).get("host") or "")
    mine = _load(out_dir, "backlinks_overview", client, lambda: client.call("get_backlinks_overview", {"target": host}))
    serp = _load(out_dir, "serp_competitors", None, None, quiet=True) or {}
    vis = {_host(c.get("domain")): c for c in (serp.get("competitors") or [] if isinstance(serp, dict) else [])
           if isinstance(c, dict)}
    mc = (market or {}).get("competitors")
    if isinstance(mc, dict):  # raw find_serp_competitors response: {"competitors": [{"domain": ...}, ...]}
        mc = mc.get("competitors") or []
    if isinstance(mc, list):  # rows may be competitor dicts or bare domains
        mc = [c.get("domain") if isinstance(c, dict) else c for c in mc]
        mc = [c for c in mc if isinstance(c, str) and c]
    mc = [c for c in (mc or []) if _host(c) not in (host, _host((site or {}).get("host", "")))][:5] if mc else None
    comps = [_host(c) for c in (mc or DEFAULT_COMPETITORS)]
    comps = [c for c in comps if _load(out_dir, f"backlinks_{c}", None, None, quiet=True) or client] or [_host(c) for c in DEFAULT_COMPETITORS]
    rows = []
    for dom in [host] + [c for c in comps if c != host]:
        d = mine if dom == host else _load(out_dir, f"backlinks_{dom}", client,
                                           lambda dom=dom: client.call("get_backlinks_overview", {"target": dom}))
        s = _summary(d)[0]
        if not s:
            log.warning("backlinks: no summary for %s", dom)
        rows.append({"domain": dom, "self": dom == host, "rank": s.get("rank"), "rd": s.get("referringDomains"),
                     "bl": s.get("backlinks"), "broken": s.get("brokenBacklinks"), "spam": s.get("targetSpamScore"),
                     "vis": (vis.get(dom) or {}).get("visibility"), "etv": (vis.get(dom) or {}).get("etv")})
    return host, mine, rows


def _n(x, fmt="{:,}"):
    return fmt.format(x) if isinstance(x, (int, float)) else "n/a"


def _analyse(host, mine, rows):
    summ, trends, newlost, refs = _summary(mine)
    a = {"summ": summ, "rows": sorted(rows, key=lambda r: -(r["rank"] or -1))}
    me = next(r for r in rows if r["self"])
    comps = [r for r in rows if not r["self"] and r["rank"] is not None]
    a["ahead_rank"] = [r for r in comps if (r["rank"] or 0) > (me["rank"] or 0)]
    a["ahead_rd"] = [r for r in comps if (r["rd"] or 0) > (me["rd"] or 0)]
    a["me"], a["comps"] = me, comps
    if len(trends) >= 2:
        f, l = trends[0], trends[-1]
        bl0, bl1 = f.get("backlinks") or 0, l.get("backlinks") or 0
        rd0, rd1 = f.get("referringDomains") or 0, l.get("referringDomains") or 0
        a["trend"] = {"from": f.get("date"), "to": l.get("date"), "bl0": bl0, "bl1": bl1, "rd0": rd0, "rd1": rd1,
                      "bl_pct": (bl1 - bl0) / max(bl0, 1), "rd_pct": (rd1 - rd0) / max(rd0, 1)}
    if newlost:
        tot = {k: sum(m.get(k) or 0 for m in newlost) for k in
               ("newBacklinks", "lostBacklinks", "newReferringDomains", "lostReferringDomains")}
        a["newlost"] = tot | {"months": len(newlost),
                              "lost_months": sum((m.get("lostReferringDomains") or 0) > (m.get("newReferringDomains") or 0) for m in newlost)}
    refs = [dict(r, domain=r.get("domain") or "", backlinks=r.get("backlinks") or 0) for r in refs if isinstance(r, dict)]
    if refs:
        spam = [r for r in refs if (r.get("spamScore") or 0) >= SPAM_CUTOFF]
        dirs = [r for r in refs if DIRECTORY_RE.search(r.get("domain") or "")]
        tot_bl = sum(r.get("backlinks") or 0 for r in refs) or 1
        top = sorted(refs, key=lambda r: -(r.get("backlinks") or 0))[:10]
        a["quality"] = {"n": len(refs), "total": (mine.get("referringDomains") or {}).get("totalCount"),
                        "spam_n": len(spam), "spam_share": len(spam) / len(refs),
                        "dir_n": len(dirs), "dir_share": len(dirs) / len(refs),
                        "dir_bl_share": sum(r.get("backlinks") or 0 for r in dirs) / tot_bl,
                        "top": top, "top_dir": sum(bool(DIRECTORY_RE.search(r["domain"])) for r in top),
                        "spam_examples": sorted(spam, key=lambda r: -(r.get("spamScore") or 0))[:4]}
    return a


def _findings(host, a):
    out, me, summ = [], a["me"], a["summ"]
    table = [f"{r['domain']}: rank {_n(r['rank'])}, {_n(r['rd'])} referring domains, {_n(r['bl'])} backlinks"
             for r in a["rows"]]
    if me["rank"] is not None and (len(a["ahead_rank"]) >= 2 or len(a["ahead_rd"]) >= 2):
        out.append(_f(id="bl_authority_gap", category="trust",
                      title=(f"{len(a['ahead_rd'])} of {len(a['comps'])} local SERP competitors have more referring domains"
                             + (" despite a lower DataForSEO rank" if not a["ahead_rank"] else f"; {len(a['ahead_rank'])} out-rank the site")),
                      severity=3 if len(a["ahead_rank"]) >= 2 else 2, intent_weight=4, pages=[], page_count=len(a["comps"]), evidence=table,
                      why_it_matters="Once titles and program pages are fixed, link authority decides who holds the top organic slots for '<city> rehab' and 'detox near me', the queries that produce admissions calls.",
                      fix="Close the gap with links competitors cannot buy: hospital/health-system referral partners, university and court/EAP programs, local news on outcomes, alumni and family-program events, and Tennessee state/county resource listings.",
                      check_first=CHECK_FIRST, confidence="medium"))
    t, nl = a.get("trend"), a.get("newlost")
    if t and (t["bl_pct"] <= -0.05 or t["rd_pct"] <= -0.02):
        ev = [f"Backlinks {t['bl0']:,} -> {t['bl1']:,} ({t['bl_pct']:+.0%}) and referring domains {t['rd0']:,} -> {t['rd1']:,} ({t['rd_pct']:+.0%}) from {t['from']} to {t['to']}"]
        if nl:
            ev.append(f"Last {nl['months']} months: +{nl['newReferringDomains']} / -{nl['lostReferringDomains']} referring domains "
                      f"(net {nl['newReferringDomains'] - nl['lostReferringDomains']:+}), +{nl['newBacklinks']:,} / -{nl['lostBacklinks']:,} backlinks; "
                      f"lost outpaced new in {nl['lost_months']} of {nl['months']} months")
        ev.append(f"Broken backlinks: {_n(summ.get('brokenBacklinks'))} links point at {_n(summ.get('brokenPages'))} dead URLs on {host}")
        if a["ahead_rank"]:
            ev.append("Competitors with a higher DataForSEO rank: " + ", ".join(f"{r['domain']} ({r['rank']})" for r in a["ahead_rank"]))
        out.append(_f(id="bl_link_decay", category="trust", title=f"Link profile is shrinking: backlinks {t['bl_pct']:+.0%} and referring domains {t['rd_pct']:+.0%} over 12 months",
                      severity=3 if t["rd_pct"] <= -0.05 else 2, intent_weight=3, pages=[], page_count=max(t["rd0"] - t["rd1"], 0),
                      evidence=ev,
                      why_it_matters="A steady net loss of linking sites erodes the authority behind program and location pages; rankings for '<city> rehab' slip months later, after calls and admissions have already dropped.",
                      fix="301 every broken-backlink URL to its closest live program page; reclaim lost links (ask referrers to update moved URLs); add one earned-link source per month (partners, local press, alumni).",
                      check_first=CHECK_FIRST + " Re-export monthly to confirm the net loss is real and not a crawler artefact.",
                      confidence="medium"))
    q = a.get("quality")
    if q and (q["spam_share"] >= 0.10 or q["dir_share"] >= 0.30 or (summ.get("targetSpamScore") or 0) >= SPAM_CUTOFF):
        ev = [f"Of the top {q['n']} referring domains (of {_n(q['total'])}): {q['spam_n']} ({q['spam_share']:.0%}) have spam score >= {SPAM_CUTOFF}; "
              f"{q['dir_n']} ({q['dir_share']:.0%}) look like rehab directories/listing sites, carrying {q['dir_bl_share']:.0%} of those backlinks",
              f"DataForSEO target spam score {_n(summ.get('targetSpamScore'))} (backlinks spam score {_n(summ.get('backlinksSpamScore'))})",
              f"{q['top_dir']} of the top 10 referrers by link count are rehab/directory domains: "
              + ", ".join(f"{r['domain']} ({r['backlinks']:,}, spam {r.get('spamScore')})" for r in q["top"][:6])]
        if q["spam_examples"]:
            ev.append("Highest-spam referrers: " + ", ".join(f"{r['domain']} (spam {r['spamScore']})" for r in q["spam_examples"]))
        out.append(_f(id="bl_quality_mix", category="trust", title="Top referring domains are dominated by rehab directories and lead-gen listing sites",
                      severity=2, intent_weight=3, pages=[], page_count=q["dir_n"], evidence=ev,
                      why_it_matters="Directory links pass little authority and, in addiction treatment, many belong to call-routing lead-gen networks that compete for the same admissions calls; a profile built on them does not move '<city> rehab' rankings.",
                      fix="Stop paying for directory/listing placements; keep SAMHSA FindTreatment, Joint Commission, LegitScript and insurer directories; audit the spam >= 30 domains and disavow only clear link-network patterns.",
                      check_first=CHECK_FIRST + " Check whether the directory domains appear there and whether any route calls to a number that is not yours.",
                      confidence="medium"))
    return out[:3]


def _write_md(host, a, out_dir):
    me, t, nl, q, s = a["me"], a.get("trend"), a.get("newlost"), a.get("quality"), a["summ"]
    pos = 1 + len(a["ahead_rank"])
    L = [f"# Backlink authority: {host}\n",
         f"DataForSEO rank {_n(me['rank'])} with {_n(me['rd'])} referring domains and {_n(me['bl'])} backlinks puts {host} "
         f"#{pos} of {len(a['comps']) + 1} against the local SERP competitors below; {len(a['ahead_rd'])} of them have more referring domains."]
    if t:
        L.append(f"Over 12 months backlinks went {t['bl0']:,} -> {t['bl1']:,} ({t['bl_pct']:+.0%}) and referring domains "
                 f"{t['rd0']:,} -> {t['rd1']:,} ({t['rd_pct']:+.0%})"
                 + (f"; net referring domains {nl['newReferringDomains'] - nl['lostReferringDomains']:+} (+{nl['newReferringDomains']}/-{nl['lostReferringDomains']})." if nl else "."))
    if q:
        L.append(f"Quality: {q['spam_share']:.0%} of the top {q['n']} referring domains score spam >= {SPAM_CUTOFF}; "
                 f"{q['dir_share']:.0%} are rehab directories/listings ({q['top_dir']} of the top 10). Target spam score {_n(s.get('targetSpamScore'))}.")
    L.append(f"Broken backlinks: {_n(s.get('brokenBacklinks'))} (to {_n(s.get('brokenPages'))} dead pages).\n")
    L += ["| # | Domain | DataForSEO rank | Referring domains | Backlinks | Broken | Target spam | SERP visibility |",
          "|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(a["rows"], 1):
        name = f"**{r['domain']}**" if r["self"] else r["domain"]
        L.append(f"| {i} | {name} | {_n(r['rank'])} | {_n(r['rd'])} | {_n(r['bl'])} | {_n(r['broken'])} | {_n(r['spam'])} | {_n(r['vis'], '{:.2f}')} |")
    if q:
        L += ["\n## Top referring domains\n", "| Domain | Backlinks | Rank | Spam | Directory? |", "|---|---|---|---|---|"]
        L += [f"| {r['domain']} | {r['backlinks']:,} | {r.get('rank')} | {r.get('spamScore')} | {'yes' if DIRECTORY_RE.search(r['domain']) else ''} |" for r in q["top"]]
    L.append("\nSource: OpenSEO / DataForSEO backlinks overview. Verify in Search Console > Links before acting.")
    with open(os.path.join(out_dir, "backlinks.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")


def run(site: dict, market: dict | None, out_dir: str, client=None) -> list:
    try:
        host, mine, rows = _collect(site, market, out_dir, client)
        if not _summary(mine)[0]:
            log.warning("backlinks: no backlink summary for %s; skipping", host)
            return []
        a = _analyse(host, mine, rows)
        try:
            _write_md(host, a, out_dir)
        except Exception as e:
            log.warning("backlinks: could not write backlinks.md: %s", e)
        return _findings(host, a)
    except Exception as e:
        log.warning("backlinks: failed: %s", str(e)[:200])
        return []
