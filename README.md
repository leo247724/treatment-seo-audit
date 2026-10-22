# treatment-seo-audit

Audits an addiction or mental-health treatment website and ranks its SEO problems by how much they probably cost in phone calls and admissions. One command per site. Output is a ranked report with evidence, a fix and a "check this first in Search Console / call tracking" note per finding.

Written in Python with Claude Code for the elev8 Product Performance Lead exercise. The crawler and checks were built inside the 90 minutes. The market-data calls go to OpenSEO, a self-hosted tool I built earlier.

Example run: `memo.md` / `memo.pdf` (Cumberland Heights, Nashville) and the raw outputs in `out/cumberlandheights.org/`.

## Quick start

```bash
./setup.sh                                   # venv, dependencies, .env, config check
.venv/bin/python audit.py https://www.example.org --city "City, ST" --brand "Facility Name"
```

No keys at all? You can still reproduce the Cumberland Heights report from the data committed in this repo, in about 20 seconds, spending nothing:

```bash
.venv/bin/python audit.py https://www.cumberlandheights.org --reuse --no-psi --city "Nashville, TN" --brand "Cumberland Heights" --ai-results out/cumberlandheights.org/ai_answers_manual.json
```

`audit.py --doctor` tells you which data sources are configured before you run.

## What OpenMarketing and OpenSEO are

The audit has two halves. The **crawler half** looks at the site itself and needs no account or key. The **market-data half** needs rankings, search results, Google Maps results and backlinks, which only a data vendor has. Commercial tools for that are Ahrefs or Semrush at a few hundred dollars a month.

I run my own stack instead. **OpenMarketing** is a set of open-source marketing tools (SEO, analytics, outreach, CRM, automation) that I self-host on one server and reach over a private network. The only piece this audit uses is **OpenSEO**, an open-source, self-hosted equivalent of Ahrefs (source: github.com/every-app/open-seo). OpenSEO does not have its own index; it buys the data per request from **DataForSEO**, a pay-as-you-go API that sells Google rankings, SERP snapshots, Maps results and backlink data. A full audit of one site costs a few hundred DataForSEO credits, roughly a dollar or two.

OpenSEO exposes its tools through an **MCP server**. MCP (Model Context Protocol) is a small HTTP JSON-RPC interface that AI agents such as Claude Code call to use external tools. This script talks to it like any HTTP API: one POST per tool call, no SDK, see `seo_audit/openseo.py`. That is also how I used it during the exercise: Claude Code called OpenSEO's tools directly to pull the data that is now cached in `out/cumberlandheights.org/openseo/`.

To run the market-data half yourself you need an OpenSEO instance you can reach. The endpoint in `.env.example` is mine and lives on a private network, so it will not answer from outside. Options: self-host OpenSEO with a DataForSEO account (its README covers it), or read the cached JSON already in this repo with `--reuse`.

## What it does

1. Crawls the site: robots.txt, sitemap(s), up to 200 HTML pages, highest-intent URLs first. Records status, title, meta, H1, canonical, noindex, word count, JSON-LD types, `tel:` links, header phone, addresses, maps, forms, FAQ blocks, accreditation / insurer / medical-review mentions.
2. Runs on-site checks grouped by what costs calls: conversion (click-to-call, insurance and admissions pages, payer names, 24/7 message, forms), local (location pages, NAP, phone variants, schema), trust (Joint Commission / CARF / LegitScript, reviewer bylines, staff credentials), technical (sitemap, broken links, redirects, noindex, canonicals, titles, thin pages, viewport, mixed content), AI visibility (robots rules for the AI citation bots, llms.txt, entity clarity of the homepage, FAQ blocks).
3. Pulls market data from OpenSEO (DataForSEO behind it): domain traffic estimate, top ranked keywords, keywords where Google AI Overviews cite the domain, local-pack rankings, live SERPs for the city's rehab queries, Google Maps results from the city centre, competitor visibility, backlink totals and trend. Turns them into findings: where the traffic really lands, whether commercial keywords rank via the homepage, 3-pack membership and rating gap, AI Overview citation mix, backlink decay.
4. Checks AI answers. Three ways: hand-run queries recorded in a JSON file (what I did, see `out/cumberlandheights.org/ai_answers_manual.json`), the Perplexity API if a key is set, or nothing (the report then says the check was not done).
5. Runs four deeper analyses. Each writes its own file and adds its findings to the ranked list; a module that is missing or fails is logged and skipped.
   - Backlinks: compares the site's backlink profile and domain authority with the competitors that win its local searches.
   - On-page: scores each high-intent page on its on-page optimization and writes a per-page scorecard.
   - Competitor pages: looks at the pages that win the SERPs and lists what they do that the site's pages do not.
   - GEO mentions: measures how often AI answers name the site versus its competitors (share of voice), from `geo_mentions.json`.
6. Optionally runs Google PageSpeed Insights on four high-intent pages.
7. Scores and ranks everything, writes the report.

## Keys and credentials

Python 3.11+ is the only requirement to run the crawler half. The table lists every variable the script reads. Put them in `.env` (copy `.env.example`); `audit.py` reads that file itself, nothing to export or source.

| Variable | Needed for | Cost | Where to get it |
|---|---|---|---|
| `OPENSEO_MCP_URL` | Market data: ranked keywords, SERPs, Maps, backlinks, AI Overview citations | Each run spends DataForSEO credits through OpenSEO, roughly 300-600 per site | Your OpenSEO deployment's MCP endpoint. Mine is `https://agi-tools.tailec481c.ts.net/mcp` and is reachable only on my tailnet. OpenSEO is open source: github.com/every-app/open-seo |
| `OPENSEO_PROJECT_ID` | Same | none | `list_projects` on that MCP server, or the project URL in the OpenSEO UI |
| `PSI_API_KEY` | PageSpeed Insights / Core Web Vitals | free | Google Cloud Console, enable "PageSpeed Insights API", create an API key. Without a key Google allows only a handful of calls per day; my run hit that limit, so CWV is unmeasured in the example output |
| `PERPLEXITY_API_KEY` | Letting the script run the AI-answer queries itself (model `sonar`) | a few cents per query | perplexity.ai API settings. Optional: I ran the queries by hand and recorded them in a JSON file instead |

Nothing else needs a key. The crawler identifies itself as `TreatmentSEOAudit/0.1` and respects robots.txt. Geocoding the city for the Maps check uses OpenStreetMap Nominatim, one request, no key.

## Flags

- `--max-pages N` crawl cap, default 150
- `--city "City, ST"` the facility's city for the market queries; otherwise taken from the first street address found, which only works for one-word city names
- `--brand "Name"` brand for the AI queries; default is the first part of the homepage title
- `--ai-results file.json` hand-checked AI answers to ingest (format below)
- `--no-psi` skip PageSpeed, `--no-openseo` skip market data
- `--skip a,b` skip pieces by name: `backlinks`, `onpage`, `competitor_pages`, `geo_mentions`, `openseo`, `psi`. `--skip openseo,psi` is the same as `--no-openseo --no-psi`.
- `--reuse` re-score from the cached crawl, PSI and OpenSEO data of the previous run. Seconds instead of minutes, spends no credits, needs no keys. Use this for demos and for reproducing the committed report.
- `--doctor` print which keys are set, whether OpenSEO answers, and which cached runs exist

A full run takes 3-8 minutes depending on how fast the site responds. The run behind the memo:

```bash
.venv/bin/python audit.py https://www.cumberlandheights.org --max-pages 200 --brand "Cumberland Heights" --city "Nashville, TN" --ai-results out/cumberlandheights.org/ai_answers_manual.json --no-psi
```

## Output

Everything lands in `out/<host>/`:

- `report.md` ranked findings. Top 5 in full, the rest in a table and a details section, then what passed, links to the deeper analyses, the AI-bot access table, PageSpeed numbers if any, the AI answer checks, and the limits of the run.
- `findings.json` the same findings as data.
- `pages.csv` one row per crawled URL with everything the crawler extracted.
- `market.md` OpenSEO snapshot: traffic estimate, which domains win the local SERPs, and the layout of each live SERP.
- `backlinks.md` backlink and domain-authority comparison with the competitors.
- `onpage.md` per-page on-page optimization scorecard.
- `competitor_pages.md` what the SERP winners' pages do differently.
- `geo_mentions.json` AI answer share of voice against the competitors; the table is copied into `report.md`.
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
setup.sh                 one-time install + config check
audit.py                 CLI
seo_audit/crawl.py       crawler and page extraction
seo_audit/classify.py    page type and intent weight from URL/title
seo_audit/checks.py      on-site checks
seo_audit/openseo.py     OpenSEO MCP client, market-data checks
seo_audit/ai_visibility.py  AI bot access, entity, FAQ, live answer checks
seo_audit/pagespeed.py   PageSpeed Insights
seo_audit/backlinks.py   backlink and domain-authority audit vs competitors -> backlinks.md
seo_audit/onpage.py      per-page on-page scorecard -> onpage.md
seo_audit/competitor_pages.py  what the SERP winners' pages do differently -> competitor_pages.md
seo_audit/geo_mentions.py  AI answer share of voice vs competitors, reads geo_mentions.json
seo_audit/report.py      scoring, ranking, report.md / findings.json / pages.csv
```
