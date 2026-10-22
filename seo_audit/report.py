"""Scoring, ranking and output (report.md, findings.json, pages.csv)."""
import csv
import json
import os
from datetime import date

from .models import Finding
from .checks import html_pages, indexable, hi


def rank(findings: list[Finding]) -> list[Finding]:
    for f in findings:
        f.score()
    return sorted(findings, key=lambda f: (-f.impact, -f.severity, -f.page_count))


def passes(site, findings, access):
    ids = {f.id for f in findings}
    out = []
    idx = indexable(site)
    if "ai_bots_blocked" not in ids:
        out.append("robots.txt does not block any AI citation bot (OAI-SearchBot, ChatGPT-User, PerplexityBot, Claude-SearchBot, Googlebot, Bingbot)")
    if site["sitemap_sources"]:
        out.append(f"XML sitemap found ({len(site['sitemap_urls'])} URLs) at {site['sitemap_sources'][0]}")
    if "no_tel_link" not in ids:
        out.append("Every indexable page has a click-to-call tel: link")
    if "no_accreditation" not in ids:
        out.append("Joint Commission / CARF accreditation is mentioned on the site")
    if "org_schema" not in ids:
        out.append("Homepage has Organization schema with telephone, address and sameAs")
    if "viewport_missing" not in ids and idx:
        out.append("All indexable pages have a mobile viewport tag")
    if "noindex_high_intent" not in ids:
        out.append("No program/location/admissions page is noindexed")
    if "no_insurance_page" not in ids:
        out.append("An insurance/cost page exists")
    return out


DEEPER_ANALYSES = [
    ("backlinks.md", "Backlink and domain-authority audit against the competitors that win the local searches."),
    ("onpage.md", "Per-page on-page optimization scorecard for the high-intent pages."),
    ("competitor_pages.md", "What the pages ranking at the top of the SERPs do that this site's pages do not."),
    ("geo_mentions.md", "Share of voice in AI answers against the competitors."),
    ("link_opportunities.md", "Link gap: domains that link to competitors but not to this site, classified and ranked, plus the directories AI engines cite."),
    ("topical_authority.md", "Topical authority matrix vs competitors and the keyword gap by topic."),
]


def deeper_analyses(out_dir):
    """Markdown lines linking the deeper-analysis files present in out_dir, plus the AI share-of-voice table."""
    L = []
    for name, desc in DEEPER_ANALYSES:
        if os.path.exists(os.path.join(out_dir, name)):
            L.append(f"- [{name}]({name}) {desc}")
    geo_json = os.path.join(out_dir, "geo_mentions.json")
    if os.path.exists(geo_json):
        try:
            from .geo_mentions import share_of_voice_table
            with open(geo_json) as fh:
                table = share_of_voice_table(json.load(fh))
            if table:
                L.append("\n### AI answer share of voice\n")
                L.append(table)
        except Exception as e:  # missing module or malformed file must not break the report
            L.append(f"\nShare-of-voice table not available ({e.__class__.__name__}: {e}).")
    return L


def write_outputs(site, findings, psi_results, ai_results, access, out_dir, brand=""):
    os.makedirs(out_dir, exist_ok=True)
    pages = list(site["pages"].values())
    idx = indexable(site)
    with open(os.path.join(out_dir, "findings.json"), "w") as fh:
        json.dump([f.to_dict() for f in findings], fh, indent=2)
    with open(os.path.join(out_dir, "pages.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["url", "final_url", "status", "redirects", "page_type", "intent_weight", "indexable", "in_sitemap",
                    "title", "title_len", "meta_desc_len", "h1_count", "main_words", "tel_links", "header_tel",
                    "canonical", "meta_robots", "jsonld_types", "has_faq", "has_map", "addresses", "forms", "fetch_ms", "error"])
        for p in pages:
            w.writerow([p.url, p.final_url, p.status, p.redirects, p.page_type, p.intent_weight, p.indexable, p.in_sitemap,
                        p.title, len(p.title), len(p.meta_description), len(p.h1s), p.main_word_count, "|".join(p.tel_links),
                        p.header_has_tel, p.canonical, p.meta_robots, "|".join(p.jsonld_types), p.has_faq, p.has_map,
                        " || ".join(p.addresses), p.forms, p.fetch_ms, p.error])
    summary = {"site": site["host"], "date": str(date.today()), "pages_crawled": len(pages),
               "pages_html_200": len(html_pages(site)), "pages_indexable": len(idx),
               "sitemap_urls": len(site["sitemap_urls"]), "uncrawled_queue": site["uncrawled"],
               "robots_status": site["robots_status"], "llms_txt_status": site["llms_txt_status"],
               "ai_bot_access": access, "psi": psi_results, "top_findings": [f.id for f in findings[:5]]}
    with open(os.path.join(out_dir, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)

    L = []
    L.append(f"# SEO audit: {site['host']}\n")
    L.append(f"Date: {date.today()} · Pages crawled: {len(pages)} · HTML 200: {len(html_pages(site))} · Indexable: {len(idx)} · "
             f"Sitemap URLs: {len(site['sitemap_urls'])} · Left in queue: {site['uncrawled']}\n")
    L.append("Impact = severity (1-5) × intent weight of affected pages (1-5) × reach (1-2, log of pages hit). "
             "Intent weight: home/admissions/insurance = 5, location/program = 4, about = 2, blog = 1. "
             "Confidence says how much to trust the automated check before a human looks.\n")
    L.append("## Top 5 problems ranked by likely cost in calls and admissions\n")
    for i, f in enumerate(findings[:5], 1):
        L.append(f"### {i}. {f.title}")
        L.append(f"Impact {f.impact} · severity {f.severity}/5 · intent {f.intent_weight}/5 · pages hit {f.page_count} · confidence {f.confidence} · category {f.category}\n")
        L.append("Evidence:")
        L.extend(f"- {e}" for e in f.evidence[:8])
        L.append(f"\nWhy it costs admissions: {f.why_it_matters}\n")
        L.append(f"Fix: {f.fix}\n")
        L.append(f"Check first (GSC / call tracking): {f.check_first}\n")
    L.append("## All findings\n")
    L.append("| # | Impact | Sev | Intent | Pages | Conf | Category | Finding |")
    L.append("|---|---|---|---|---|---|---|---|")
    for i, f in enumerate(findings, 1):
        L.append(f"| {i} | {f.impact} | {f.severity} | {f.intent_weight} | {f.page_count} | {f.confidence} | {f.category} | {f.title} |")
    L.append("\n## Finding details\n")
    for f in findings[5:]:
        L.append(f"### {f.title}")
        L.append(f"Impact {f.impact} · severity {f.severity} · intent {f.intent_weight} · pages {f.page_count} · confidence {f.confidence}\n")
        L.extend(f"- {e}" for e in f.evidence[:8])
        if f.pages:
            L.append(f"- Example pages: {', '.join(f.pages[:5])}")
        L.append(f"\nWhy: {f.why_it_matters}\n\nFix: {f.fix}\n\nCheck first: {f.check_first}\n")
    L.append("## What passed\n")
    L.extend(f"- {p}" for p in passes(site, findings, access))
    deeper = deeper_analyses(out_dir)
    if deeper:
        L.append("\n## Deeper analyses\n")
        L.extend(deeper)
    L.append("\n## AI crawler access (robots.txt)\n")
    L.append("| Bot | Allowed | Feeds |")
    L.append("|---|---|---|")
    from .ai_visibility import AI_BOTS
    for b, ok in access.items():
        L.append(f"| {b} | {'yes' if ok else 'NO'} | {AI_BOTS[b][0]} |")
    if psi_results:
        L.append("\n## PageSpeed Insights (mobile)\n")
        L.append("| URL | Score | Lab LCP | Field LCP | Field INP | Field CLS | CrUX |")
        L.append("|---|---|---|---|---|---|---|")
        for r in psi_results:
            if "error" in r:
                L.append(f"| {r['url']} | error | | | | | {r['error'][:40]} |")
            else:
                L.append(f"| {r['url']} | {r['perf_score']} | {r['lab_lcp_s']}s | {r['field_lcp_ms']} | {r['field_inp_ms']} | {r['field_cls']} | {r['field_overall'] or 'none'} |")
    if ai_results:
        L.append("\n## AI answer checks\n")
        L.append("| Engine | Query | Site cited | Brand mentioned | Who was cited |")
        L.append("|---|---|---|---|---|")
        for r in ai_results:
            L.append(f"| {r.get('engine')} | {r['query']} | {r.get('cited', r.get('error', '?'))} | {r.get('brand_mentioned', '')} | {', '.join(r.get('cited_domains', [])[:6])} |")
    L.append("\n## Limitations\n")
    L.append("- Static HTML only: content injected by JavaScript (chat widgets, some forms, dynamic phone numbers) is not seen. Confirm 'no form' / 'no tel link' findings in a browser.")
    L.append("- No rankings, traffic or call data: impact is an estimate from page intent, not measured loss. Search Console and call tracking turn these into numbers.")
    L.append(f"- Crawl capped at {len(pages)} pages, high-intent URLs first; deep blog archives may be under-sampled.")
    L.append("- Phone-number variants may be intentional call-tracking swaps.")
    L.append("- AI answer checks are a snapshot of a few queries on one day; answers vary by user, location and time.")
    with open(os.path.join(out_dir, "report.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")
    return os.path.join(out_dir, "report.md")
