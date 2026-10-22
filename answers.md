# Two short answers

## Where was the AI wrong or unreliable, and how did I catch it?

1. **The crawler's first ranking put 404 image files at #1.** My URL classifier assigned "insurance" and "campus" intent to image filenames (e.g. `.../alcohol-drug-addiction-treatment-insurance-accepted-aetna.png`, `.../stillwater-mens-campus-14.jpg`), so dead attachment URLs from the Yoast image sitemap scored impact 40 and "broken links on high-intent pages" topped the report. I caught it by reading the evidence lines instead of the headline: every "linked from 0 pages, e.g. sitemap" entry was a `/wp-content/uploads/` file. Fix: exclude assets from sitemap seeds and crawl, add an "archive" page type for tag/category URLs.
2. **The crawler reported 22 "redirect chains" that were my own doing.** It normalised URLs by stripping trailing slashes; WordPress 301s them back. Removing my normalisation removed the finding.
3. **Perplexity cited a noindexed ads landing page (cumberlandheights.com) as a source for the brand.** An AI engine quoting a page the site owner explicitly hid from search is a reminder that AI answer checks need the cited URLs inspected, not just "was the brand mentioned".
4. **My draft memo stated two things the data later disproved.** I wrote "the homepage has no Organization schema" and "0 of 15 program pages have an FAQ" from the first (flawed) crawl. The corrected crawl showed Yoast emits Organization/MedicalOrganization/MedicalClinic on the homepage (incomplete: no telephone, address or sameAs) and that the detox page and the admissions FAQ do carry FAQPage schema. Both sentences were rewritten before sending. Lesson: never let a memo claim outrun the run that produced it.
5. **42 blog URLs came back HTTP 500 and 106 timed out during the crawl, which the report scored as "broken pages".** Re-fetching five of them alone returned 200 in 4-7 seconds; the site was simply overloaded by my crawler plus OpenSEO's Lighthouse run. I reclassified it as a server-speed observation and said so in the memo.
6. **PageSpeed Insights returned 429 for every page** (daily quota, no API key). The report says "not measured" rather than guessing a score.

Method: every automated finding carries a confidence level, the memo's top 5 were each checked against a second source (DataForSEO SERPs, Google Maps results, Perplexity citations, a browser visit), and I kept the raw JSON for every call in `out/cumberlandheights.org/`.

## What I would improve with another 10 hours

- **Measured impact instead of estimated.** Connect GSC and GA4 through OpenSEO's connectors and call-tracking exports: calls per landing page, CTR by query for the homepage, brand-query trend. The intent-weight model becomes a regression on real calls.
- **Rendered crawl.** Playwright pass for the top 30 pages to catch JS-injected forms, chat widgets and dynamic phone numbers; the static crawl cannot see them.
- **AI visibility as a tracked metric.** Run a fixed 25-query panel weekly across ChatGPT (search), Perplexity, Gemini and Google AI Mode, log cited domains, and plug in Ansvisor from the OpenMarketing stack for share-of-voice over time.
- **GBP audit module.** Pull every listing (15+ locations), compare name/category/phone/hours/website against the site, review velocity vs competitors, and flag listings whose website link redirects.
- **Competitor gap pages.** From `find_serp_competitors`, diff the ranking URL structures (city + level of care pages) and generate the page briefs, with payer and FAQ blocks, that close the gap.
- **Core Web Vitals properly.** PSI with an API key plus CrUX field data for the 10 highest-intent pages, mobile only.
- **Scoring calibration.** Replace the hand-set severity × intent × reach weights with weights fitted on a few elev8 client sites where call outcomes are known, and surface the confidence per finding in the memo automatically.
