# treatment-seo-audit

Audits an addiction or mental-health treatment website and ranks its SEO problems by how much they probably cost in phone calls and admissions. One command per site. Output is a ranked report with evidence, a fix and a "check this first in Search Console / call tracking" note per finding.

Written in Python with Claude Code for the elev8 Product Performance Lead exercise. The crawler and checks were built inside the 90 minutes. The market-data calls go to OpenSEO, a self-hosted tool I built earlier.

Example run: `memo.md` / `memo.pdf` (Cumberland Heights, Nashville) and the raw outputs in `out/cumberlandheights.org/`.

## What it does

1. Crawls the site: robots.txt, sitemap(s), up to 200 HTML pages, highest-intent URLs first. Records status, title, meta, H1, canonical, noindex, word count, JSON-LD types, `tel:` links, header phone, addresses, maps, forms, FAQ blocks, accreditation / insurer / medical-review mentions.
2. Runs on-site checks grouped by what costs calls: conversion (click-to-call, insurance and admissions pages, payer names, 24/7 message, forms), local (location pages, NAP, phone variants, schema), trust (Joint Commission / CARF / LegitScript, reviewer bylines, staff credentials), technical (sitemap, broken links, redirects, noindex, canonicals, titles, thin pages, viewport, mixed content), AI visibility (robots rules for the AI citation bots, llms.txt, entity clarity of the homepage, FAQ blocks).
3. Pulls market data from OpenSEO (DataForSEO behind it): domain traffic estimate, top ranked keywords, keywords where Google AI Overviews cite the domain, local-pack rankings, live SERPs for the city's rehab queries, Google Maps results from the city centre, competitor visibility, backlink totals and trend. Turns them into findings: where the traffic really lands, whether commercial keywords rank via the homepage, 3-pack membership and rating gap, AI Overview citation mix, backlink decay.
4. Checks AI answers. Three ways: hand-run queries recorded in a JSON file (what I did, see `out/cumberlandheights.org/ai_answers_manual.json`), the Perplexity API if a key is set, or nothing (the report then says the check was not done).
5. Optionally runs Google PageSpeed Insights on four high-intent pages.
6. Scores and ranks everything, writes the report.

## Requirements

- Python 3.11+ and `uv` (or plain `venv` + `pip`)
- Network access to the site
- For market data: an OpenSEO instance (see keys below). Without it the crawler-only checks still run.

```bash
uv venv .venv
uv pip install -p .venv/bin/python -r requirements.txt
```

## Keys and credentials

| Variable | Needed for | Cost | Where to get it |
|---|---|---|---|
| `OPENSEO_MCP_URL` | Market data: ranked keywords, SERPs, Maps, backlinks, AI Overview citations | Each run spends DataForSEO credits through OpenSEO, roughly 300-600 per site | Your OpenSEO deployment's MCP endpoint. Mine is `https://agi-tools.tailec481c.ts.net/mcp` and is reachable only on my tailnet. OpenSEO is open source: github.com/every-app/open-seo |
| `OPENSEO_PROJECT_ID` | Same | none | `list_projects` on that MCP server, or the project URL in the OpenSEO UI |
| `PSI_API_KEY` | PageSpeed Insights / Core Web Vitals | free | Google Cloud Console, enable "PageSpeed Insights API", create an API key. Without a key Google allows only a handful of calls per day; my run hit that limit, so CWV is unmeasured in the example output |
| `PERPLEXITY_API_KEY` | Letting the script run the AI-answer queries itself (model `sonar`) | a few cents per query | perplexity.ai API settings. Optional: I ran the queries by hand and recorded them in a JSON file instead |

Nothing else needs a key. The crawler identifies itself as `TreatmentSEOAudit/0.1` and respects robots.txt. Geocoding the city for the Maps check uses OpenStreetMap Nominatim, one request, no key.

Put the values in `.env` (there is a `.env.example`) and load them before running:

```bash
cp .env.example .env
set -a; source .env; set +a
```

## Run

```bash
.venv/bin/python audit.py https://www.example.org --brand "Example Recovery" --city "Nashville, TN"
```

Flags:

- `--max-pages N` crawl cap, default 150
- `--city "City, ST"` the facility's city for the market queries; otherwise taken from the first street address found, which only works for one-word city names
- `--brand "Name"` brand for the AI queries; default is the first part of the homepage title
- `--ai-results file.json` hand-checked AI answers to ingest (format below)
- `--no-psi` skip PageSpeed, `--no-openseo` skip market data
- `--reuse` re-score from the cached crawl, PSI and OpenSEO data of the previous run. Seconds instead of minutes, spends no credits. Use this for demos.

A full run takes 3-8 minutes depending on how fast the site responds. The run behind the memo:

```bash
.venv/bin/python audit.py https://www.cumberlandheights.org --max-pages 200 --brand "Cumberland Heights" --city "Nashville, TN" --ai-results out/cumberlandheights.org/ai_answers_manual.json --no-psi
```

## Output

Everything lands in `out/<host>/`:

- `report.md` ranked findings. Top 5 in full, the rest in a table and a details section, then what passed, the AI-bot access table, PageSpeed numbers if any, the AI answer checks, and the limits of the run.
- `findings.json` the same findings as data.
- `pages.csv` one row per crawled URL with everything the crawler extracted.
- `market.md` OpenSEO snapshot: traffic estimate, which domains win the local SERPs, and the layout of each live SERP.
- `openseo/*.json` raw DataForSEO responses. `ai_answers.json`, `ai_queries.txt`, `summary.json`.
- `crawl.pkl`, `psi.json` caches for `--reuse`.

## How the ranking works

```
impact = severity (1-5) × intent weight of the pages affected (1-5) × reach (1 to 2, log10 of pages hit)
```

Intent weight comes from the URL and title: homepage, admissions, insurance, contact = 5; location and program pages = 4; about pages = 2; blog and archives = 1. A broken link on a blog post and a broken link on the insurance page are different problems and score differently. Each finding also carries a confidence (high / medium / low) that says how much to trust the automated check before someone looks at the page. The report prints the evidence lines, not just the headline, because the headline was wrong more than once while building this (see `answers.md`).

## AI answer file format

A JSON list. `type` is `brand` or `non-brand`; `cited` means the site's own domain appeared in the answer's sources.

```json
[{"engine": "perplexity", "type": "non-brand", "query": "best alcohol rehab in Nashville, TN",
  "cited": false, "brand_mentioned": true, "cited_domains": ["rehab.com", "startyourrecovery.org"],
  "note": "named, but sourced from directories"}]
```

## What it does not do

- It reads static HTML. Forms, chat widgets and phone numbers injected by JavaScript are invisible. Confirm any "no form" or "no phone link" finding in a browser.
- It has no rankings, traffic or call data of its own beyond DataForSEO estimates. Impact is an estimate from page intent; Search Console and call tracking turn it into numbers.
- The crawl stops at the page cap. Large blog archives are sampled, not covered.
- Several phone numbers on a site can be deliberate call-tracking swaps.
- AI answer checks are a snapshot of a few queries on one day.
- Sites behind aggressive bot protection return 403 and are reported as blocked.
- If the site is slow, a 6-thread crawl plus any other crawler hitting it at the same time will produce timeouts and 500s that are not real page errors. The Cumberland Heights run had that; the memo says so.

## Layout

```
audit.py                 CLI
seo_audit/crawl.py       crawler and page extraction
seo_audit/classify.py    page type and intent weight from URL/title
seo_audit/checks.py      on-site checks
seo_audit/openseo.py     OpenSEO MCP client, market-data checks
seo_audit/ai_visibility.py  AI bot access, entity, FAQ, live answer checks
seo_audit/pagespeed.py   PageSpeed Insights
seo_audit/report.py      scoring, ranking, report.md / findings.json / pages.csv
```
