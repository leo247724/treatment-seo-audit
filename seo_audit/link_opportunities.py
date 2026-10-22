"""Link-gap and mention opportunities: referring domains that link to local competitors but not to the site,
plus the third-party domains AI engines cite in rehab answers (via OpenSEO get_backlinks_profile).

run(site, market, out_dir, client=None) -> list[Finding]. With client=None it reads only cached JSON under
<out_dir>/openseo/backlink_rows_<domain>_p<N>.json. It never raises."""
import json
import logging
import os
import re
from collections import Counter, defaultdict
from urllib.parse import urlparse

from .checks import _f
from .openseo import _cached

log = logging.getLogger("audit")

COMPETITORS = ["recoveryranch.com", "southeastaddictiontn.com", "nashvilleaddictionrecovery.com",
               "liveagaindetox.com", "apex.rehab"]
COMP_PAGES, SELF_MAX_PAGES = 2, 6
ARGS = {"mode": "one_per_domain", "pageSize": 100, "hideSpam": True, "sortField": "domainRank", "sortOrder": "desc",
        "filters": {"linkType": "dofollow"}}
NOISE = re.compile(r"safelinks|outlook\.com$|translate\.goog|webcache|googleusercontent|bing\.com$|archive\.org$|"
                   r"hostingersite|wpdns|^(staging|dev|test)\.|ift\.tt|xxx|2ch\.|digikala|\.home\.blog$|blogspot|"
                   r"\.(?!(com|org|net|edu|gov|us|mil|info|io|co|news|health|rehab|care|tv|fm|biz|uk|ca)$)[a-z]+$")
SPAMDIR = re.compile(r"storeboard|provenexpert|zumvu|intelius|bunity|hotfrog|cylex|brownbook|merchantcircle|citysquares|"
                     r"ezlocal|chamberofcommerce\.com|adforum|weblink|justlink|avjobs|usi32|gisuser|bizcommunity|n49\.")
KNOWN_DIR = {"psychologytoday.com", "yelp.com", "bbb.org", "healthgrades.com", "rehab.com", "recovery.com", "rehabs.org",
             "startyourrecovery.org", "rehabnet.com", "rehabseekers.com", "drugrehab.com", "recovered.org",
             "findtreatment.gov", "alcohol.org", "drugabuse.com", "therecoveryvillage.com", "yellowpages.com", "manta.com", "indeed.com", "glassdoor.com", "zocdoc.com"}
NEWS = re.compile(r"huffpost|huffingtonpost|buzzfeed|bustle|vice\.com|insider|dailybeast|scarymommy|goodmenproject|"
                  r"rawstory|thefix|livescience|thoughtcatalog|jezebel|inkl\.com|playboy|globenewswire|prnewswire|"
                  r"news|times|tribune|herald|gazette|journal|press|daily|magazine|tennessean|patch\.com|iheart|podcast|"
                  r"radio|^(w|k)[a-z]{2,3}(tv|fm|am)?\.(com|org|net)$|^(fox|abc|cbs|nbc|channel|newschannel)\d+|bizjournals")
GOV = re.compile(r"\.gov$|\.gov\.|\.us$|\.mil$|civicplus|county|^(cityof|townof)|\.state\.")
DIRW = re.compile(r"rehab|addiction|detox|recovery|treatment|sober|directory|listing|finder|locator")
HEALTH = re.compile(r"hospital|health|medical|clinic|care|medicine|physician|vumc|hca")
ASSOC = re.compile(r"association|foundation|council|coalition|church|alliance|society|chamber|\.org$")
ANGLE = {"news/media": "Pitch an outcomes or alumni-recovery story (local angle, data from the alumni program)",
         "education": "Offer a student-health / collegiate-recovery resource for their counseling resource page",
         "government": "Ask to be added to the county/city behavioral-health resource list",
         "health system": "Propose a referral-partner listing (detox/residential step-down) on their partner page",
         "association": "Join or renew membership and request the member-directory listing",
         "directory": "Claim the profile; complete insurers, levels of care, photos",
         "blog/other": "Offer an expert quote or guest resource on family/relapse topics"}
MENTION_ACT = {"psychologytoday.com": "Claim/complete the treatment-center listing; add every insurer and level of care, photos",
               "yelp.com": "Claim the page, fix NAP and categories, reply to every review, ask alumni for reviews",
               "bbb.org": "Claim/accredit the profile, fix NAP, answer complaints publicly",
               "google.com": "Complete Google Business Profile; collect reviews",
               "indeed.com": "Claim the employer page and answer reviews (AI engines quote it in 'reviews' answers)"}
DEFAULT_ACT = "Claim or complete the listing; add insurers, levels of care, photos; fix NAP; collect reviews"
CHECK_FIRST = ("Search Console > Links > 'Top linking sites' (export): confirm each target below is truly absent before "
               "outreach, since DataForSEO only samples the top ~200 dofollow domains per competitor.")


def _host(u):
    h = (urlparse(u if "//" in (u or "") else "//" + (u or "")).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def classify(d):
    if d in KNOWN_DIR or any(d.endswith("." + k) for k in KNOWN_DIR) or SPAMDIR.search(d):
        return "directory"
    if d.endswith(".edu") or ".edu." in d or d.endswith(".k12.tn.us"):
        return "education"
    for typ, rx in (("government", GOV), ("news/media", NEWS), ("directory", DIRW), ("health system", HEALTH),
                    ("association", ASSOC)):
        if rx.search(d):
            return typ
    return "directory" if "center" in d else "blog/other"


def _page(out_dir, dom, n, client):
    """One page of rows: cached file when usable, live call only with a client (re-fetches cached error stubs)."""
    name = f"backlink_rows_{dom}_p{n}"
    path = os.path.join(out_dir, "openseo", f"{name}.json")
    data = None
    if os.path.exists(path):
        try:
            with open(path) as fh:
                data = json.load(fh)
        except Exception:
            data = None
    if client is not None and (not isinstance(data, dict) or "error" in data):
        data = _cached(out_dir, name, False, lambda: client.call("get_backlinks_profile", {"target": dom, "page": n, **ARGS}))
    bl = (data or {}).get("backlinks") or {} if isinstance(data, dict) else {}
    return bl.get("rows") or [], bool(bl.get("hasMore")), bl.get("totalCount")


def _rows(out_dir, dom, client, max_pages):
    rows, total = [], None
    for n in range(1, max_pages + 1):
        r, more, tc = _page(out_dir, dom, n, client)
        rows += r
        total = total or tc
        if not more or not r:
            break
    return rows, total


def _gap(host, mine, comp_rows):
    have = {_host(r.get("domainFrom") or r.get("urlFrom")) for r in mine}
    skip = {host, *COMPETITORS}
    gap = {}
    for comp, rows in comp_rows.items():
        for r in rows:
            d = _host(r.get("domainFrom") or r.get("urlFrom"))
            if not d or d in have or NOISE.search(d) or any(d == s or d.endswith("." + s) for s in skip):
                continue
            g = gap.setdefault(d, {"domain": d, "type": classify(d), "rank": 0, "competitors": [], "example_url": "",
                                   "anchor": "", "competitor_target": "", "first_seen": ""})
            if comp not in g["competitors"]:
                g["competitors"].append(comp)
            rk = r.get("domainFromRank") or 0
            if rk >= g["rank"] or not g["example_url"]:
                g.update(rank=max(rk, g["rank"]), example_url=r.get("urlFrom") or "", anchor=(r.get("anchor") or "")[:80],
                         competitor_target=r.get("urlTo") or "", first_seen=(r.get("firstSeen") or "")[:10])
    for g in gap.values():
        g["competitors_linked"] = len(g["competitors"])
        g["score"] = round(g["rank"] * (1 + 0.5 * g["competitors_linked"]) * (0.3 if g["type"] == "directory" else 1), 1)
        g["outreach_angle"] = ANGLE[g["type"]]
    return sorted(gap.values(), key=lambda g: (-g["score"], g["domain"]))


def _mentions(out_dir, mine, comp_rows):
    def load(name):
        try:
            with open(os.path.join(out_dir, name)) as fh:
                return json.load(fh)
        except Exception:
            return None
    geo, manual = load("geo_mentions.json") or {}, load("ai_answers_manual.json") or []
    brands = {_host(d) for b in geo.get("brands", []) for d in b.get("domains", [])} | set(COMPETITORS)
    cnt, answers = Counter(), 0
    for q in geo.get("queries", []):
        answers += 1
        cnt.update({_host(u) for u in q.get("citations", [])} | {_host(u) for u in q.get("directory_domains_cited", [])})
    for a in manual if isinstance(manual, list) else []:
        answers += 1
        cnt.update({_host(u) for u in a.get("cited_domains", [])})
    have = {_host(r.get("domainFrom") or r.get("urlFrom")) for r in mine}
    comp_have = {c: {_host(r.get("domainFrom") or "") for r in rows} for c, rows in comp_rows.items()}
    out = []
    for d, n in cnt.most_common():
        if not d or d in brands or any(d.endswith("." + b) for b in brands):
            continue
        linked = any(h == d or h.endswith("." + d) for h in have)
        out.append({"domain": d, "answers_citing": n, "type": classify(d), "site_has_link": linked,
                    "competitors_with_link": sum(any(h == d or h.endswith("." + d) for h in s) for s in comp_have.values()),
                    "action": MENTION_ACT.get(d, DEFAULT_ACT if classify(d) == "directory" else ANGLE[classify(d)])})
    return out, answers


def _md(host, gap, ments, answers, comp_rows, mine_n, mine_total):
    L = [f"# Link and mention opportunities: {host}", "",
         f"Method: OpenSEO `get_backlinks_profile` (DataForSEO; one link per domain, dofollow, spam hidden, sorted by "
         f"domain rank). Competitors: top 200 referring domains each ({', '.join(COMPETITORS)}). Site: {mine_n} of "
         f"{mine_total or '?'} referring domains pulled. Gap = linking domain absent from the site's pulled rows. "
         f"Score = domain rank x (1 + 0.5 x competitors linked); directories x0.3 (mostly pay-to-play). Low-rank gap "
         f"domains may already link to the site beyond the pulled sample: verify in GSC before outreach.", "",
         f"**{len(gap)} gap domains**: " + ", ".join(f"{t} {n}" for t, n in Counter(g['type'] for g in gap).most_common()),
         "", "## Top 40 link-gap opportunities", "",
         "| # | Domain | Type | Rank | Comps | Example linking page (anchor) | Links to | Outreach angle |",
         "|---|---|---|---|---|---|---|---|"]
    for i, g in enumerate(gap[:40], 1):
        L.append(f"| {i} | {g['domain']} | {g['type']} | {g['rank']} | {g['competitors_linked']} | {g['example_url'][:90]} "
                 f"({g['anchor'][:40] or '-'}) | {_host(g['competitor_target'])} | {g['outreach_angle']} |")
    L += ["", f"## Mention opportunities: domains AI engines cite ({answers} answers)", "",
          "| Domain | Answers citing | Type | Site has backlink | Competitors with link | Action |", "|---|---|---|---|---|---|"]
    for m in ments[:25]:
        L.append(f"| {m['domain']} | {m['answers_citing']} | {m['type']} | {'yes' if m['site_has_link'] else 'no'} | "
                 f"{m['competitors_with_link']} | {m['action']} |")
    L += ["", "## Patterns", ""]
    for comp, rows in comp_rows.items():
        mine = [g for g in gap if comp in g["competitors"]]
        types = Counter(g["type"] for g in mine).most_common(3)
        top = ", ".join(g["domain"] for g in sorted(mine, key=lambda g: -g["rank"])[:3])
        L.append(f"- **{comp}**: {len(mine)} of its {len(rows)} sampled domains are gaps; mostly "
                 f"{', '.join(f'{t} ({n})' for t, n in types) or 'none'}; strongest: {top or 'n/a'}.")
    return "\n".join(L) + "\n"


def run(site, market, out_dir, client=None):
    try:
        host = _host((site or {}).get("start_url") or (site or {}).get("host") or "cumberlandheights.org")
        mine, mine_total = _rows(out_dir, host, client, SELF_MAX_PAGES)
        comp_rows = {c: _rows(out_dir, c, client, COMP_PAGES)[0] for c in COMPETITORS}
        comp_rows = {c: r for c, r in comp_rows.items() if r}
        if not mine or not comp_rows:
            log.warning("link_opportunities: missing rows (site %d, competitors %d)", len(mine), len(comp_rows))
            return []
        gap = _gap(host, mine, comp_rows)
        ments, answers = _mentions(out_dir, mine, comp_rows)
        with open(os.path.join(out_dir, "link_opportunities.json"), "w") as fh:
            json.dump({"host": host, "competitors": list(comp_rows), "site_rows": len(mine), "site_total": mine_total,
                       "gap": gap, "mentions": ments, "answers": answers}, fh, indent=1)
        with open(os.path.join(out_dir, "link_opportunities.md"), "w") as fh:
            fh.write(_md(host, gap, ments, answers, comp_rows, len(mine), mine_total))
        return _findings(host, gap, ments, answers)
    except Exception as e:
        log.warning("link_opportunities failed: %s", str(e)[:200])
        return []


def _findings(host, gap, ments, answers):
    out = []
    by = Counter(g["type"] for g in gap)
    earned = [g for g in gap if g["type"] != "directory"]
    if gap:
        top10 = "; ".join(f"{g['domain']} ({g['type']}, rank {g['rank']}): {g['outreach_angle'].split(' (')[0]}"
                          for g in gap[:10])
        out.append(_f(id="link_gap_competitors", category="trust", severity=4 if len(earned) >= 50 else 3, intent_weight=4,
                      title=f"{len(gap)} referring domains link to Nashville competitors but not to {host}",
                      pages=[g["example_url"] for g in gap[:5]],
                      page_count=len(gap),
                      evidence=[f"Gap domains: {len(gap)} ({', '.join(f'{t} {n}' for t, n in by.most_common())})",
                                f"Linking to 2+ competitors: {sum(g['competitors_linked'] >= 2 for g in gap)}",
                                "Top 5: " + ", ".join(f"{g['domain']} ({g['type']}, rank {g['rank']}, "
                                                      f"{g['competitors_linked']} comps)" for g in gap[:5])],
                      why_it_matters=("Organic #1 for 'alcohol rehab Nashville' and the local pack both weigh prominence; "
                                      "these editorial, health-system and civic domains already vouch for competitors, "
                                      "so each one closed narrows the authority gap where it counts locally."),
                      fix="Work the first 10 targets in order: " + top10 + ". Full list in link_opportunities.md.",
                      check_first=CHECK_FIRST, confidence="medium"))
    missing = [m for m in ments if not m["site_has_link"]][:10]
    if missing:
        out.append(_f(id="ai_cited_listing_gaps", category="trust", severity=3, intent_weight=4,
                      title=f"{len(missing)} of the domains AI engines cite most give {host} no backlink",
                      pages=[], page_count=len(missing),
                      evidence=[f"{answers} AI answers analysed (geo_mentions.json + ai_answers_manual.json)",
                                "Most cited without a site link: " + ", ".join(
                                    f"{m['domain']} ({m['answers_citing']})" for m in missing[:5])],
                      why_it_matters=("AI answers and the local pack lean on these listings for NAP, insurers and "
                                      "reviews; incomplete or unclaimed profiles mean the brand is described from "
                                      "third-party data and the site itself is not cited."),
                      fix="; ".join(f"{m['domain']}: {m['action']}" for m in missing[:6]) + ".",
                      check_first="Search Console > Links report (Top linking sites) plus each listing's admin panel.",
                      confidence="medium"))
    return out
