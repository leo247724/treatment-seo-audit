# Treatment-center SEO audit

A small, re-runnable workflow that crawls an addiction or mental-health treatment website and ranks its SEO problems by how much they likely cost the facility in **calls and admissions**, not just traffic. Built with Claude Code (Fable 5.1) in the 90-minute elev8 Product Performance Lead exercise; the OpenMarketing stack it calls was built earlier.

## Run it

```bash
uv venv .venv && uv pip install -p .venv/bin/python -r requirements.txt   # or: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # set OPENSEO_MCP_URL + OPENSEO_PROJECT_ID (market data backbone), optional PERPLEXITY_API_KEY / PSI_API_KEY
set -a; source .env; set +a
.venv/bin/python audit.py https://www.example.org --brand "Example Recovery" --city "Nashville, TN"
```

Takes 3-6 minutes: ~2 min crawl (200 pages, high-intent URLs first), ~1-2 min of OpenSEO/DataForSEO calls (a few hundred credits per site), plus ~30-60 s per PageSpeed call. `--no-psi` skips PageSpeed, `--no-openseo` skips market data, `--reuse` re-scores from the cached crawl and cached market data in seconds (no credits), `--ai-results file.json` ingests hand-checked AI answers.

The exact run behind `memo.md`:

```bash
.venv/bin/python audit.py https://www.cumberlandheights.org --max-pages 200 --brand "Cumberland Heights" --city "Nashville, TN" --ai-results out/cumberlandheights.org/ai_answers_manual.json --no-psi
```

Outputs land in `out/<host>/`:

| File | What |
|---|---|
| `report.md` | Ranked findings, top 5 with evidence / why it costs admissions / fix / what to check first in GSC and call tracking, passes, AI-bot access table, PageSpeed table, limitations |
| `findings.json` | Same findings, machine-readable |
| `pages.csv` | One row per crawled URL: status, page type, intent weight, title, tel links, schema, word count... |
| `summary.json` | Crawl stats, AI bot access, PSI results |
| `ai_queries.txt` | The AI-answer queries to run by hand if no API key is set |
| `market.md` | OpenSEO snapshot: estimated traffic, who wins the local SERPs, live SERP layouts |
| `openseo/*.json` | Raw DataForSEO responses (ranked keywords, AI Overview citations, local pack, SERPs, Maps, backlinks) |
| `crawl.pkl`, `psi.json` | Caches for `--reuse` |

## What it checks

- **Conversion**: click-to-call `tel:` links on every page and in the header, insurance / admissions / cost pages, payer names, "verify insurance" CTA, 24/7 messaging, forms.
- **Local**: location pages with NAP + map + LocalBusiness/MedicalClinic schema, address variants, phone-number variants, Organization schema on the homepage.
- **Trust (E-E-A-T for YMYL)**: Joint Commission / CARF / LegitScript mentions, medical-review bylines on program and blog pages, staff credentials.
- **Technical**: robots.txt, sitemap coverage and dead URLs, noindex and canonical on high-intent pages, broken links, redirect chains, titles / descriptions / H1s, thin program pages, viewport, mixed content, Core Web Vitals via the free PageSpeed Insights API.
- **Market data (OpenSEO / DataForSEO, the off-site backbone)**: where the organic traffic actually lands (blog vs money pages), whether commercial "<city> rehab" keywords rank through dedicated pages or the homepage, 3-pack membership on live SERPs, Google Maps rank and rating gap vs the top 3 from the city centre, GBP website-link health, which pages Google AI Overviews cite, backlink trend and spam.
- **AI visibility**: robots.txt access for citation bots (OAI-SearchBot, ChatGPT-User, PerplexityBot, Claude-SearchBot, Googlebot, Bingbot) vs training bots, llms.txt, entity clarity of the homepage title/H1, FAQ / direct-answer blocks on program pages, and live answer-engine presence.

## How ranking works

`impact = severity (1-5) × intent weight of the pages hit (1-5) × reach (1-2, log of pages hit)`

Intent weight comes from URL/title classification: home, admissions, insurance, contact = 5; location and program pages = 4; about = 2; blog = 1. A broken link on a blog post and a broken link on the insurance page are not the same problem. Every finding carries a **confidence** (high / medium / low) that says how far to trust the automated check before a human looks.

## AI-answer checks

Three ways, in order of preference:

1. **Manual** (free, most reliable): run the queries in `out/<host>/ai_queries.txt` in ChatGPT (search on), Perplexity and Google, record them in a JSON file like `out/cumberlandheights.org/ai_answers_manual.json`, and re-run with `--ai-results that.json --reuse`.
2. **Perplexity API**: set `PERPLEXITY_API_KEY` and the audit runs the queries through the `sonar` model (a few cents per query).
3. **OpenSEO / DataForSEO** (optional, what I used for the cross-check): ranked keywords with `resultTypes: ai_overview_reference` show which queries the domain is cited in Google AI Overviews for; `get_serp_results` shows local-pack membership and whether an AI Overview is present.

## OpenMarketing / OpenSEO

The market-data half runs on my self-hosted OpenMarketing stack: OpenSEO (DataForSEO-backed) exposes an MCP server, and `seo_audit/openseo.py` is a 20-line JSON-RPC client that calls `get_domain_overview`, `get_ranked_keywords` (organic, `ai_overview_reference`, `local_pack`), `get_serp_results`, `find_serp_competitors`, `get_local_serp_results` and `get_backlinks_overview`, caches every response as JSON and turns them into findings. Any OpenSEO deployment works: set `OPENSEO_MCP_URL` and `OPENSEO_PROJECT_ID`. Without them the crawler-only checks still run.

## Limitations (read before trusting a finding)

- Static HTML only. JavaScript-injected forms, chat widgets and dynamic phone numbers are invisible; confirm "no form" / "no tel link" in a browser.
- No rankings, traffic or call data of its own. Impact is an estimate from page intent; Search Console and call tracking turn it into numbers.
- 150-page cap. Deep blog archives are under-sampled by design (high-intent URLs crawl first).
- Phone-number variants may be intentional call-tracking swaps.
- AI answers are a one-day snapshot of a few queries; they vary by user, location and time.
- Sites behind aggressive bot protection (Cloudflare "bot fight") return 403 and are reported as blocked, not as errors on the site.
