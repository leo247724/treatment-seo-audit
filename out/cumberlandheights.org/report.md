# SEO audit: cumberlandheights.org

Date: 2026-10-21 · Pages crawled: 150 · HTML 200: 37 · Indexable: 37 · Sitemap URLs: 3234 · Left in queue: 3084

Impact = severity (1-5) × intent weight of affected pages (1-5) × reach (1-2, log of pages hit). Intent weight: home/admissions/insurance = 5, location/program = 4, about = 2, blog = 1. Confidence says how much to trust the automated check before a human looks.

## Top 5 problems ranked by likely cost in calls and admissions

### 1. Internal links to broken (4xx/5xx) pages
Impact 40.0 · severity 4/5 · intent 5/5 · pages hit 23 · confidence medium · category technical

Evidence:
- https://www.cumberlandheights.org/wp-content/uploads/2016/06/alcohol-drug-addiction-treatment-insurance-accepted-aetna.png -> HTTP 404 (linked from 0 pages, e.g. sitemap)
- https://www.cumberlandheights.org/wp-content/uploads/2025/01/2023_10_02_stillwater-womens-campus-3.jpg.webp -> HTTP 404 (linked from 0 pages, e.g. sitemap)
- https://www.cumberlandheights.org/wp-content/uploads/2021/11/2023_09_25_stillwater-mens-campus-14-e1781722166674.jpg -> HTTP 404 (linked from 0 pages, e.g. sitemap)
- https://www.cumberlandheights.org/wp-content/uploads/2025/01/2023_10_02_stillwater-womens-campus-7-1.webp -> HTTP 404 (linked from 0 pages, e.g. sitemap)
- https://www.cumberlandheights.org/wp-content/uploads/2024/09/2023_09_25_stillwater-mens-campus-29-1.webp -> HTTP 404 (linked from 0 pages, e.g. sitemap)
- https://www.cumberlandheights.org/wp-content/uploads/2024/09/2023_09_25_stillwater-mens-campus-24-1.webp -> HTTP 404 (linked from 0 pages, e.g. sitemap)
- https://www.cumberlandheights.org/wp-content/uploads/2025/01/2023_09_25_stillwater-mens-campus-18.jpg.webp -> HTTP 404 (linked from 0 pages, e.g. sitemap)
- https://www.cumberlandheights.org/wp-content/uploads/2024/09/2023_09_25_stillwater-mens-campus-14-1.webp -> HTTP 404 (linked from 0 pages, e.g. sitemap)

Why it costs admissions: A prospect clicking a dead 'Admissions' or program link leaves; link equity is lost.

Fix: Redirect or fix the targets, then update the source links.

Check first (GSC / call tracking): GSC > Pages > Not found (404): which have impressions? Call tracking: calls from these landing URLs before they broke.

### 2. Sitemap lists URLs that do not return 200
Impact 30.0 · severity 3/5 · intent 5/5 · pages hit 23 · confidence medium · category technical

Evidence:
- https://www.cumberlandheights.org/wp-content/uploads/2016/06/alcohol-drug-addiction-treatment-insurance-accepted-aetna.png -> HTTP 404
- https://www.cumberlandheights.org/wp-content/uploads/2025/01/2023_10_02_stillwater-womens-campus-3.jpg.webp -> HTTP 404
- https://www.cumberlandheights.org/wp-content/uploads/2021/11/2023_09_25_stillwater-mens-campus-14-e1781722166674.jpg -> HTTP 404
- https://www.cumberlandheights.org/wp-content/uploads/2025/01/2023_10_02_stillwater-womens-campus-7-1.webp -> HTTP 404
- https://www.cumberlandheights.org/wp-content/uploads/2024/09/2023_09_25_stillwater-mens-campus-29-1.webp -> HTTP 404
- https://www.cumberlandheights.org/wp-content/uploads/2024/09/2023_09_25_stillwater-mens-campus-24-1.webp -> HTTP 404
- https://www.cumberlandheights.org/wp-content/uploads/2025/01/2023_09_25_stillwater-mens-campus-18.jpg.webp -> HTTP 404
- https://www.cumberlandheights.org/wp-content/uploads/2024/09/2023_09_25_stillwater-mens-campus-14-1.webp -> HTTP 404

Why it costs admissions: Google trusts the sitemap less and wastes crawl budget on dead URLs.

Fix: Regenerate the sitemap from live, indexable URLs only.

Check first (GSC / call tracking): GSC > Pages > 'Not found (404)' and 'Redirect error' filtered to sitemap URLs.

### 3. AI answer presence not verified (no API key / no manual results)
Impact 26.7 · severity 3/5 · intent 5/5 · pages hit 6 · confidence low · category ai_visibility

Evidence:
- Queries written to ai_queries.txt. Set PERPLEXITY_API_KEY or pass --ai-results <json> after checking manually.

Why it costs admissions: Cannot rank what we did not measure; this stays a hypothesis until checked.

Fix: Run the queries, record results, re-run the audit with --ai-results.

Check first (GSC / call tracking): n/a

### 4. Thin program/location/admissions pages (under 300 words)
Impact 25.5 · severity 3/5 · intent 5/5 · pages hit 5 · confidence medium · category content

Evidence:
- https://www.cumberlandheights.org/tag/aa-meeting-what-to-expect: 49 words
- https://www.cumberlandheights.org/tag/what-to-expect-at-an-aa-meeting: 49 words
- https://www.cumberlandheights.org/member-category/admissions: 98 words
- https://www.cumberlandheights.org/member-category/financial-services: 133 words
- https://www.cumberlandheights.org/giving/endowment-2: 279 words

Why it costs admissions: Pages that cannot answer 'what happens, who is it for, what does it cost, is it covered' rarely rank for city + program queries and are rarely quoted by AI engines.

Fix: Expand each to cover program description, levels of care, insurance, admission steps, staff, FAQ.

Check first (GSC / call tracking): GSC: impressions vs clicks per page; which program queries do these pages appear for at position 8-20?

### 5. Program and blog pages lack medical reviewer / author bylines
Impact 24.0 · severity 3/5 · intent 4/5 · pages hit 16 · confidence medium · category trust

Evidence:
- 0 of 16 program/content pages show 'medically reviewed' or a credentialed byline

Why it costs admissions: Health content without visible expertise ranks worse after Google's helpful-content/E-E-A-T updates and is less likely to be cited by AI engines.

Fix: Add 'Medically reviewed by <Name, credentials>' with a linked bio to every program and blog page.

Check first (GSC / call tracking): GSC: did blog/program clicks drop around core updates? Which pages lost positions 1-5?

## All findings

| # | Impact | Sev | Intent | Pages | Conf | Category | Finding |
|---|---|---|---|---|---|---|---|
| 1 | 40.0 | 4 | 5 | 23 | medium | technical | Internal links to broken (4xx/5xx) pages |
| 2 | 30.0 | 3 | 5 | 23 | medium | technical | Sitemap lists URLs that do not return 200 |
| 3 | 26.7 | 3 | 5 | 6 | low | ai_visibility | AI answer presence not verified (no API key / no manual results) |
| 4 | 25.5 | 3 | 5 | 5 | medium | content | Thin program/location/admissions pages (under 300 words) |
| 5 | 24.0 | 3 | 4 | 16 | medium | trust | Program and blog pages lack medical reviewer / author bylines |
| 6 | 24.0 | 3 | 4 | 15 | medium | ai_visibility | Program pages have no FAQ / direct-answer sections |
| 7 | 20.0 | 2 | 5 | 22 | medium | technical | Redirect chains and internal links to redirecting URLs |
| 8 | 19.5 | 3 | 5 | 2 | medium | content | Missing or duplicate title tags |
| 9 | 16.0 | 2 | 5 | 4 | medium | content | Missing meta descriptions |
| 10 | 10.4 | 2 | 4 | 2 | low | local | Same address written in different ways across the site |
| 11 | 10.0 | 2 | 5 | 1 | high | ai_visibility | Homepage lacks a complete Organization/MedicalOrganization schema |
| 12 | 10.0 | 2 | 5 | 1 | high | trust | Accreditation mentioned on the site but not on the homepage |
| 13 | 8.9 | 2 | 3 | 3 | low | local | 3 different phone numbers in tel: links |
| 14 | 8.9 | 1 | 5 | 6 | medium | content | Title tags too long or too short |
| 15 | 8.0 | 2 | 4 | 1 | medium | content | Missing or multiple H1 headings |
| 16 | 8.0 | 2 | 4 | 1 | medium | trust | No LegitScript certification mentioned |
| 17 | 6.0 | 2 | 3 | 0 | low | trust | No staff page with clinical credentials found |

## Finding details

### Program pages have no FAQ / direct-answer sections
Impact 24.0 · severity 3 · intent 4 · pages 15 · confidence medium

- 1 of 16 program pages have 3+ question headings or FAQPage schema
- 2 pages site-wide carry FAQPage schema
- Example pages: https://www.cumberlandheights.org/giving/endowment-2, https://www.cumberlandheights.org/treatment/extended-care, https://www.cumberlandheights.org/treatment/professionals-program, https://www.cumberlandheights.org/treatment/spiritual-care, https://www.cumberlandheights.org/treatment

Why: AI Overviews, ChatGPT and Perplexity lift 40-80 word passages that answer a question directly (cost, length of stay, insurance, detox). Without them the site is paraphrased from directories instead of cited.

Fix: Add a 4-6 question FAQ to every program/location page (what it costs, insurance, how long, what to bring, visiting, detox) with FAQPage JSON-LD.

Check first: GSC: question-style queries ('how long', 'does', 'what is') where the site ranks 5-15.

### Redirect chains and internal links to redirecting URLs
Impact 20.0 · severity 2 · intent 5 · pages 22 · confidence medium

- 22 internal links point at redirecting URLs (e.g. https://www.cumberlandheights.org/contact-us)
- Example pages: https://www.cumberlandheights.org/contact-us, https://www.cumberlandheights.org/treatment, https://www.cumberlandheights.org/treatment/drug-and-alcohol-detox, https://www.cumberlandheights.org/treatment/residential-care, https://www.cumberlandheights.org/treatment/adolescent-care

Why: Each hop adds latency on mobile and leaks ranking signals.

Fix: Update internal links to final URLs; collapse chains to a single 301.

Check first: GSC crawl stats: redirect share of crawl requests.

### Missing or duplicate title tags
Impact 19.5 · severity 3 · intent 5 · pages 2 · confidence medium

- 0 missing
- 'Admissions - Cumberland Heights' used on 2 pages
- Example pages: https://www.cumberlandheights.org/admissions, https://www.cumberlandheights.org/member-category/admissions

Why: The title is the ad headline in search; duplicates make program pages compete with each other.

Fix: Unique titles: '<Program> in <City>, <ST> | <Brand>'.

Check first: GSC Performance: pages with high impressions and CTR under 2%.

### Missing meta descriptions
Impact 16.0 · severity 2 · intent 5 · pages 4 · confidence medium

- 4 of 37 indexable pages
- Example pages: https://www.cumberlandheights.org/tag/aa-meeting-what-to-expect, https://www.cumberlandheights.org/tag/what-to-expect-at-an-aa-meeting, https://www.cumberlandheights.org/member-category/admissions, https://www.cumberlandheights.org/member-category/financial-services

Why: Google writes its own snippet, usually without the phone number, insurance or '24/7' hook.

Fix: Write descriptions that state program, location, insurance accepted and a call prompt.

Check first: GSC: CTR on high-impression program pages.

### Same address written in different ways across the site
Impact 10.4 · severity 2 · intent 4 · pages 2 · confidence low

- '8283 River Rd Pike Nashville, TN 37209' (36 pages) | '8283 River Road Pike Nashville, TN 37209' (1 pages)

Why: NAP inconsistency between site, GBP and citations erodes local pack trust.

Fix: Pick one canonical format per facility (match GBP exactly) and use it in footer, location pages and schema.

Check first: Compare against GBP listing and top citations (Psychology Today, SAMHSA locator).

### Homepage lacks a complete Organization/MedicalOrganization schema
Impact 10.0 · severity 2 · intent 5 · pages 1 · confidence high

- Homepage JSON-LD types: ['BreadcrumbList', 'ListItem', 'Organization', 'WebPage', 'WebSite', 'WebPage', 'ImageObject', 'BreadcrumbList', 'ListItem', 'WebSite', 'Organization', 'MedicalOrganization', 'MedicalClinic', 'WebSite', 'WebPage', 'MedicalTherapy', 'MedicalTherapy', 'MedicalTherapy', 'MedicalTherapy', 'MedicalTherapy', 'MedicalTherapy', 'MedicalTherapy', 'MedicalTherapy', 'INVALID_JSON']
- telephone: no, address: no, sameAs: no
- Example pages: https://www.cumberlandheights.org/

Why: Entity data (name, phone, address, sameAs to GBP/Wikipedia/socials) is how Google and AI engines confirm who you are. It feeds the knowledge panel and AI answer citations.

Fix: Add MedicalOrganization JSON-LD with name, url, logo, telephone, address, areaServed, medicalSpecialty, sameAs[].

Check first: GSC: Enhancements/Rich results reports; search the brand name and see whether a knowledge panel appears.

### Accreditation mentioned on the site but not on the homepage
Impact 10.0 · severity 2 · intent 5 · pages 1 · confidence high

- Mentioned on 5 pages, e.g. https://www.cumberlandheights.org/admissions/faqs
- Example pages: https://www.cumberlandheights.org/

Why: Most first visits land on the homepage; the seal belongs there and in the footer.

Fix: Add the seal and a one-line statement to the footer template.

Check first: None.

### 3 different phone numbers in tel: links
Impact 8.9 · severity 2 · intent 3 · pages 3 · confidence low

- 800-646-9998: on 44 pages (e.g. https://www.cumberlandheights.org/member-category/admissions)
- 615-314-3856: on 37 pages (e.g. https://www.cumberlandheights.org/member-category/admissions)
- 620-416-2213: on 1 pages (e.g. https://www.cumberlandheights.org/admissions/faqs)

Why: Multiple numbers can be legitimate call-tracking swaps, but if they are hard-coded they fragment NAP consistency and Google Business Profile matching.

Fix: One primary admissions number in schema and footer; use dynamic number insertion (CallRail/CTM) for tracking rather than hard-coded variants.

Check first: Call tracking: are these pool numbers? If any number is not in the tracking tool, find who owns it.

### Title tags too long or too short
Impact 8.9 · severity 1 · intent 5 · pages 6 · confidence medium

- 6 over 65 chars, 0 under 25 chars
- 84 chars: Introduction to AA Meetings: What to Expect on Your First Visit - Cumberland Hei
- 70 chars: What to Expect During Detox: A Step-by-Step Guide - Cumberland Heights
- 94 chars: The Many Benefits You Can Find Through Sober Living Homes: What to Expect - Cumb
- Example pages: https://www.cumberlandheights.org/resources/blog/introduction-to-aa-meetings-what-to-expect-on-your-first-visit, https://www.cumberlandheights.org/resources/blog/what-to-expect-during-detox-a-step-by-step-guide, https://www.cumberlandheights.org/resources/blog/the-many-benefits-you-can-find-through-sober-living-homes-what-to-expect, https://www.cumberlandheights.org/resources/news-article/people-can-change-justin-furstenfelds-unique-approach-book-tour, https://www.cumberlandheights.org/resources/podcast/pathways-to-healing-the-admissions-journey-with-robin-todd

Why: Truncated titles hide the location or program name in results.

Fix: Keep the program + city in the first 55 characters.

Check first: GSC CTR by page vs. position.

### Missing or multiple H1 headings
Impact 8.0 · severity 2 · intent 4 · pages 1 · confidence medium

- 1 pages with no H1, 0 with more than one
- Example pages: https://www.cumberlandheights.org/young-mens-summit

Why: Weak topical signal for program/location pages.

Fix: One H1 per page naming the service and place.

Check first: None needed; template fix.

### No LegitScript certification mentioned
Impact 8.0 · severity 2 · intent 4 · pages 1 · confidence medium

- No page mentions LegitScript
- Example pages: https://www.cumberlandheights.org/

Why: LegitScript certification is required to run Google/Meta ads for addiction treatment and is a visible trust badge; its absence may also mean paid search is unavailable.

Fix: Get certified (if not) and show the badge in the footer.

Check first: Check legitscript.com certified list for the facility.

### No staff page with clinical credentials found
Impact 6.0 · severity 2 · intent 3 · pages 0 · confidence low

- 0 staff/team pages crawled; none list MD/LCSW/LADAC-style credentials in text

Why: Named clinicians with credentials are what families, Google raters and AI engines use to judge legitimacy.

Fix: Clinical team page with photo, name, credentials, role; Person schema.

Check first: None.

## What passed

- robots.txt does not block any AI citation bot (OAI-SearchBot, ChatGPT-User, PerplexityBot, Claude-SearchBot, Googlebot, Bingbot)
- XML sitemap found (3234 URLs) at https://www.cumberlandheights.org/sitemap.xml
- Every indexable page has a click-to-call tel: link
- Joint Commission / CARF accreditation is mentioned on the site
- All indexable pages have a mobile viewport tag
- No program/location/admissions page is noindexed
- An insurance/cost page exists

## AI crawler access (robots.txt)

| Bot | Allowed | Feeds |
|---|---|---|
| OAI-SearchBot | yes | ChatGPT search index: the source of ChatGPT citations |
| ChatGPT-User | yes | ChatGPT live browsing when a user asks |
| PerplexityBot | yes | Perplexity index |
| Perplexity-User | yes | Perplexity live fetch |
| Claude-SearchBot | yes | Claude search index |
| Claude-User | yes | Claude live fetch |
| Googlebot | yes | Google Search and AI Overviews / AI Mode |
| Bingbot | yes | Bing, Copilot; also a ChatGPT search fallback |
| GPTBot | yes | OpenAI model training |
| ClaudeBot | yes | Anthropic model training |
| anthropic-ai | yes | Anthropic (legacy token) |
| Google-Extended | yes | Gemini training/grounding opt-out; does NOT affect AI Overviews |
| CCBot | yes | Common Crawl, used by many model builders |
| Applebot-Extended | yes | Apple Intelligence training |
| Bytespider | yes | ByteDance training |
| meta-externalagent | yes | Meta AI training |

## PageSpeed Insights (mobile)

| URL | Score | Lab LCP | Field LCP | Field INP | Field CLS | CrUX |
|---|---|---|---|---|---|---|
| https://www.cumberlandheights.org/resources/blog/sunday-sermon-liberation-is-costly | error | | | | | 429 Client Error: Too Many Requests for  |
| https://www.cumberlandheights.org/ | error | | | | | 429 Client Error: Too Many Requests for  |
| https://www.cumberlandheights.org/resources/blog/introducing-arch-academys-ridgeview-campus | error | | | | | 429 Client Error: Too Many Requests for  |
| https://www.cumberlandheights.org/giving/endowment-2 | error | | | | | 429 Client Error: Too Many Requests for  |

## Limitations

- Static HTML only: content injected by JavaScript (chat widgets, some forms, dynamic phone numbers) is not seen. Confirm 'no form' / 'no tel link' findings in a browser.
- No rankings, traffic or call data: impact is an estimate from page intent, not measured loss. Search Console and call tracking turn these into numbers.
- Crawl capped at 150 pages, high-intent URLs first; deep blog archives may be under-sampled.
- Phone-number variants may be intentional call-tracking swaps.
- AI answer checks are a snapshot of a few queries on one day; answers vary by user, location and time.
