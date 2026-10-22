"""How the site can (or cannot) show up in AI answers: crawler access, entity data, answer-ready content, live checks."""
import json
import os
import re
from urllib import robotparser
from urllib.parse import urlparse

import requests

from .models import Finding
from .checks import html_pages, indexable, urls, _f

# bot -> (what it feeds, role). role "cite" = blocking removes you from answers; "train" = model training only.
AI_BOTS = {
    "OAI-SearchBot": ("ChatGPT search index: the source of ChatGPT citations", "cite"),
    "ChatGPT-User": ("ChatGPT live browsing when a user asks", "cite"),
    "PerplexityBot": ("Perplexity index", "cite"),
    "Perplexity-User": ("Perplexity live fetch", "cite"),
    "Claude-SearchBot": ("Claude search index", "cite"),
    "Claude-User": ("Claude live fetch", "cite"),
    "Googlebot": ("Google Search and AI Overviews / AI Mode", "cite"),
    "Bingbot": ("Bing, Copilot; also a ChatGPT search fallback", "cite"),
    "GPTBot": ("OpenAI model training", "train"),
    "ClaudeBot": ("Anthropic model training", "train"),
    "anthropic-ai": ("Anthropic (legacy token)", "train"),
    "Google-Extended": ("Gemini training/grounding opt-out; does NOT affect AI Overviews", "train"),
    "CCBot": ("Common Crawl, used by many model builders", "train"),
    "Applebot-Extended": ("Apple Intelligence training", "train"),
    "Bytespider": ("ByteDance training", "train"),
    "meta-externalagent": ("Meta AI training", "train"),
}

CATEGORY_RE = re.compile(r"treatment|rehab|recovery|addiction|behavioral|mental health|detox|substance", re.I)
CITY_RE = re.compile(r"([A-Za-z.]+),\s*([A-Z]{2})\s+\d{5}$")  # last word before ", ST ZIP"; multi-word cities need --city


def bot_access(site) -> dict:
    rp = robotparser.RobotFileParser()
    rp.parse((site.get("robots_txt") or "").splitlines())
    home = site.get("home_final_url") or site["start_url"]
    return {bot: rp.can_fetch(bot, home) for bot in AI_BOTS}


def site_city_state(site):
    if site.get("city_override"):
        c, _, st = site["city_override"].rpartition(",")
        return c.strip(), st.strip()
    for p in html_pages(site):
        for a in p.addresses:
            m = CITY_RE.search(a)
            if m:
                return m.group(1).strip(), m.group(2)
    return "", ""


def build_queries(brand: str, city: str) -> list[dict]:
    q = []
    if city:
        q += [{"query": f"best alcohol rehab in {city}", "type": "non-brand"},
              {"query": f"drug rehab in {city} that takes insurance", "type": "non-brand"},
              {"query": f"residential addiction treatment near {city}", "type": "non-brand"},
              {"query": f"inpatient mental health and addiction treatment {city}", "type": "non-brand"}]
    if brand:
        q += [{"query": f"{brand} reviews", "type": "brand"},
              {"query": f"is {brand} a good rehab, what insurance does it take", "type": "brand"}]
    return q


def perplexity_check(queries, host, brand, key, timeout=60) -> list[dict]:
    """Optional live check through the Perplexity API (model 'sonar'). Costs a few cents per query."""
    out = []
    for q in queries:
        body = {"model": "sonar", "messages": [{"role": "user", "content": q["query"]}],
                "return_citations": True}
        try:
            r = requests.post("https://api.perplexity.ai/chat/completions", json=body, timeout=timeout,
                              headers={"Authorization": f"Bearer {key}"})
            r.raise_for_status()
            d = r.json()
        except requests.RequestException as e:
            out.append({**q, "engine": "perplexity", "error": str(e)})
            continue
        answer = d["choices"][0]["message"]["content"]
        cites = d.get("citations") or d.get("search_results") or []
        cite_urls = [c if isinstance(c, str) else c.get("url", "") for c in cites]
        hosts = [urlparse(u).netloc.lower().replace("www.", "") for u in cite_urls]
        out.append({**q, "engine": "perplexity", "cited": host in hosts,
                    "brand_mentioned": bool(brand) and brand.lower() in answer.lower(),
                    "cited_domains": sorted(set(hosts))[:12], "answer_excerpt": answer[:400]})
    return out


def check_ai_visibility(site, brand="", ai_results=None, out_dir=None):
    findings = []
    host = site["host"]
    pages = html_pages(site)
    idx = indexable(site)
    home = next((p for p in pages if p.page_type == "home"), None)

    # 1. crawler access
    access = bot_access(site)
    blocked_cite = [b for b, ok in access.items() if not ok and AI_BOTS[b][1] == "cite"]
    blocked_train = [b for b, ok in access.items() if not ok and AI_BOTS[b][1] == "train"]
    if blocked_cite:
        findings.append(_f(id="ai_bots_blocked", category="ai_visibility", title="robots.txt blocks AI answer engines from citing the site",
                           severity=5, intent_weight=5, pages=[site["start_url"] + "robots.txt"], page_count=len(blocked_cite),
                           evidence=[f"{b} blocked: {AI_BOTS[b][0]}" for b in blocked_cite],
                           why_it_matters="If ChatGPT search or Perplexity cannot fetch the site, they answer 'best rehab in <city>' with competitors only.",
                           fix="Allow the citation bots (OAI-SearchBot, ChatGPT-User, PerplexityBot, Claude-SearchBot). Blocking training bots (GPTBot, CCBot) is a separate decision.",
                           check_first="Server logs: which AI user agents hit the site in the last 30 days. GSC is blind to this.",
                           confidence="high"))
    if blocked_train:
        findings.append(_f(id="ai_train_bots_blocked", category="ai_visibility", title="Training-only AI bots blocked (informational)",
                           severity=1, intent_weight=2, pages=[site["start_url"] + "robots.txt"], page_count=len(blocked_train),
                           evidence=[f"{b}: {AI_BOTS[b][0]}" for b in blocked_train],
                           why_it_matters="A policy choice, not an SEO error. Note that GPTBot is also used to seed some OpenAI retrieval, so blocking it can reduce ChatGPT brand knowledge over time.",
                           fix="Keep if intentional.", check_first="None.", confidence="high"))

    # 2. llms.txt (weak signal; be honest)
    if site.get("llms_txt_status") != 200:
        findings.append(_f(id="no_llms_txt", category="ai_visibility", title="No llms.txt", severity=1, intent_weight=2,
                           pages=[site["start_url"] + "llms.txt"], page_count=1,
                           evidence=[f"HTTP {site.get('llms_txt_status')} for /llms.txt"],
                           why_it_matters="Low weight: no major engine has confirmed using it. Cheap to add; do it after the items above.",
                           fix="Publish /llms.txt listing programs, locations, insurance page and admissions phone.",
                           check_first="None.", confidence="high"))

    # 3. entity clarity on the homepage
    if home:
        text = (home.title + " " + " ".join(home.h1s))
        city, state = site_city_state(site)
        has_cat = bool(CATEGORY_RE.search(text))
        has_loc = bool(city and city.lower() in text.lower()) or bool(state and re.search(rf"\b{state}\b|{STATE_NAMES.get(state, 'zzz')}", text, re.I))
        if not (has_cat and has_loc):
            findings.append(_f(id="home_entity_unclear", category="ai_visibility", title="Homepage title/H1 does not state what the facility is and where",
                               severity=3, intent_weight=5, pages=[home.final_url], page_count=1,
                               evidence=[f"title: '{home.title}'", f"H1: {home.h1s}",
                                         f"category term present: {has_cat}; location ({city or '?'}, {state or '?'}) present: {has_loc}"],
                               why_it_matters="AI engines and Google build the entity from the homepage. 'Brand | Home' tells them nothing; '<Brand>: Addiction Treatment Center in <City>, <ST>' is what gets quoted for '<city> rehab' answers.",
                               fix="Title: '<Brand> | Alcohol & Drug Rehab in <City>, <ST>'. H1 that names the service and place. Matching MedicalOrganization schema.",
                               check_first="GSC: does the homepage get impressions for any '<city> rehab/treatment' query? Brand vs non-brand click split.",
                               confidence="medium"))

    # 4. answer-ready content
    programs = [p for p in idx if p.page_type == "program"]
    with_faq = [p for p in programs if p.has_faq]
    faq_schema = [p for p in idx if "FAQPage" in p.jsonld_types]
    if programs and len(with_faq) < max(1, len(programs) * 0.25):
        findings.append(_f(id="no_answer_blocks", category="ai_visibility", title="Program pages have no FAQ / direct-answer sections",
                           severity=3, intent_weight=4, pages=urls([p for p in programs if not p.has_faq]), page_count=len(programs) - len(with_faq),
                           evidence=[f"{len(with_faq)} of {len(programs)} program pages have 3+ question headings or FAQPage schema",
                                     f"{len(faq_schema)} pages site-wide carry FAQPage schema"],
                           why_it_matters="AI Overviews, ChatGPT and Perplexity lift 40-80 word passages that answer a question directly (cost, length of stay, insurance, detox). Without them the site is paraphrased from directories instead of cited.",
                           fix="Add a 4-6 question FAQ to every program/location page (what it costs, insurance, how long, what to bring, visiting, detox) with FAQPage JSON-LD.",
                           check_first="GSC: question-style queries ('how long', 'does', 'what is') where the site ranks 5-15.",
                           confidence="medium"))

    # 5. live answer-engine presence
    city, state = site_city_state(site)
    place = f"{city}, {state}" if city else ""
    queries = build_queries(brand, place)
    results = list(ai_results or [])
    key = os.environ.get("PERPLEXITY_API_KEY")
    if not results and key and queries:
        results = perplexity_check(queries, host, brand, key)
    if out_dir and queries:
        with open(os.path.join(out_dir, "ai_queries.txt"), "w") as fh:
            fh.write("Run each in ChatGPT (search on), Perplexity and Google (look for AI Overview). Record: cited? brand mentioned? who was cited.\n\n")
            fh.write("\n".join(q["query"] for q in queries) + "\n")
    if results:
        nb = [r for r in results if r.get("type") == "non-brand" and "error" not in r]
        br = [r for r in results if r.get("type") == "brand" and "error" not in r]
        nb_cited = [r for r in nb if r.get("cited")]
        br_ok = [r for r in br if r.get("cited") or r.get("brand_mentioned")]
        engines = sorted({r.get("engine", "?") for r in results})
        ev = [f"Non-brand queries citing {host}: {len(nb_cited)} of {len(nb)} ({', '.join(engines)})",
              f"Brand queries that mention/cite the brand: {len(br_ok)} of {len(br)}"]
        for r in results[:8]:
            if "error" in r:
                ev.append(f"[{r.get('engine')}] '{r['query']}': ERROR {r['error'][:80]}")
            else:
                ev.append(f"[{r.get('engine')}] '{r['query']}': cited={r.get('cited')} brand_mentioned={r.get('brand_mentioned')} cited={', '.join(r.get('cited_domains', [])[:5])}")
        if nb and len(nb_cited) == 0:
            sev = 4
        elif nb and len(nb_cited) < len(nb) / 2:
            sev = 3
        else:
            sev = 0
        if br and len(br_ok) < len(br):
            sev = max(sev, 3)
        if sev:
            findings.append(_f(id="ai_answers_absent", category="ai_visibility", title="Site is absent from AI answers for local treatment queries",
                               severity=sev, intent_weight=5, pages=[r["query"] for r in nb if not r.get("cited")][:6], page_count=len(nb) - len(nb_cited),
                               evidence=ev,
                               why_it_matters="A growing share of 'best rehab near me' research starts in ChatGPT/Perplexity/AI Overviews. The sources those answers cite (directories, competitors) get the call.",
                               fix="Fix the entity + FAQ items above, get listed and reviewed on the sources the engines cite (Psychology Today, SAMHSA, Google reviews, Rehabs.com, local news), and publish a comparison-style '<city> rehab options' guide that names the facility.",
                               check_first="GSC: brand-query trend (AI exposure drives brand searches). Call tracking: ask 'how did you hear about us' and tag 'AI/ChatGPT'.",
                               confidence="high" if any(r.get("engine") != "perplexity" for r in results) else "medium"))
        results_path = os.path.join(out_dir, "ai_answers.json") if out_dir else None
        if results_path:
            with open(results_path, "w") as fh:
                json.dump(results, fh, indent=2)
    elif queries:
        findings.append(_f(id="ai_answers_unverified", category="ai_visibility", title="AI answer presence not verified (no API key / no manual results)",
                           severity=3, intent_weight=5, pages=[q["query"] for q in queries], page_count=len(queries),
                           evidence=["Queries written to ai_queries.txt. Set PERPLEXITY_API_KEY or pass --ai-results <json> after checking manually."],
                           why_it_matters="Cannot rank what we did not measure; this stays a hypothesis until checked.",
                           fix="Run the queries, record results, re-run the audit with --ai-results.",
                           check_first="n/a", confidence="low"))
    return findings, access, results


STATE_NAMES = {"AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
               "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
               "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
               "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
               "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
               "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
               "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
               "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
               "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
               "WI": "Wisconsin", "WY": "Wyoming", "DC": "Washington DC"}
