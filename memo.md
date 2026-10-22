# Cumberland Heights (cumberlandheights.org): the 5 SEO problems most likely costing calls and admissions

Cumberland Heights is a Nashville nonprofit (since 1966) with a 177-acre River Road campus plus 15+ outpatient sites, audited 21 Oct 2026 with github.com/leo247724/treatment-seo-audit plus OpenSEO/DataForSEO, Maps, SERP and Perplexity data. Problems are ranked by likely effect on calls, not traffic; figures are public-data estimates.

| # | Problem | Likely cost in calls | Fix in one line | Check first (GSC / call tracking) |
|---|---|---|---|---|
| 1 | Not in the 3-pack for core Nashville searches; 4.0★ vs 4.7-4.9★ | High | Review program; GBP aligned with the site | Calls on GBP number vs site number |
| 2 | Money keywords rank through a homepage titled "Home" | High | Service + city titles; city + program pages | GSC homepage CTR vs position |
| 3 | AI answers cite directories, skip residential | Med | FAQ answer blocks, full schema, outcomes page | GSC brand trend; "AI" source in call intake |
| 4 | Thin trust signals on health pages | Med | Medical-reviewer bylines, accreditation seals | GSC blog vs /treatment/ clicks over core updates |
| 5 | Technical SEO: sitemap, archives, phone variants, speed | Low | Clean sitemap, noindex archives, one NAP, caching | GSC Pages report; calls per number |

## The 5 problems

### 1. Missing from the Google 3-pack for core Nashville rehab searches; main listing rates 4.0★ beside competitors at 4.7-4.9★

**The residential campus is missing where mobile searchers tap to call.**

**Evidence**
- Not in the 3-pack for "alcohol rehab nashville tn", "drug rehab nashville" or "detox nashville tn"; in it only for "inpatient rehab nashville tn" (#3) and "rehab nashville tn" (#2).
- Google Maps from downtown, mobile: River Road is absent from the top 20 for "alcohol rehab" and "drug rehab"; only the Music Row outpatient listing appears (#6-7, 4.6★, 9 reviews).
- River Road GBP: 4.0★ from 234 reviews vs 4.7-4.9★ (104-410 reviews) for every pack competitor.
- Perplexity's "Cumberland Heights reviews" answer leads with Yelp 3.0★ and billing complaints.

**Why it costs calls**
- On mobile the 3-pack sits above the #1 organic result the site already holds and carries the tap-to-call button; rating is the visible tiebreaker.

**Fix**
- Review program: ask at discharge and from alumni, answer every review, fix the 1-star themes.
- Align GBP categories, services, photos and phone with the site; UTM links to each location page; Joint Commission and insurers in the description.

**Check first**
- Call tracking: GBP number (866-395-6390) vs site header number (800-646-9998); GBP Insights calls by query.
- Search Console: brand-query trend as reviews land.

### 2. Every commercial "nashville rehab" keyword ranks through a homepage titled "Home - Cumberland Heights"

**The highest-value queries land on a page titled "Home".**

**Evidence**
- DataForSEO: "rehabs nashville tn" (2,400/mo, CPC $91) #1, "nashville rehab centers" (1,300/mo, CPC $95) #1, "drug treatment nashville tn" #1, "detox nashville tn" #4, "iop nashville tn" #18, all via the homepage.
- /treatment/drug-and-alcohol-detox and /treatment/residential-care rank for no city + program query.
- Competitors rank dedicated pages (apex.rehab/tennessee/nashville/).

**Why it costs calls**
- CPCs near $90 say what each click is worth; "Home" caps click-through, and one page must convert detox, residential, IOP and insurance intent at once.

**Fix**
- Title/H1 "Cumberland Heights | Alcohol & Drug Rehab in Nashville, TN (since 1966)"; description with 24/7, insurers, Joint Commission.
- One page per city + level of care with NAP, schema, payers and FAQ, linked from the homepage hero (the 3 readable location pages under /resources/location/ carry MedicalBusiness schema; the gap is program + city pages).

**Check first**
- Search Console: homepage queries containing "nashville", CTR vs position (positions 1-3 should clear 5-8%; the gap is the title); which /treatment/ URLs get impressions for "nashville detox" or "nashville iop".
- Call tracking: calls by landing page, as a baseline.

### 3. AI answers describe the facility from directories, not its own site, and skip it for residential treatment

**AI engines quote directories, not the site.**

**Evidence**
- Perplexity, 21 Oct: 0 of 3 non-brand Nashville queries cite cumberlandheights.org; two name the facility but source startyourrecovery.org, rehab.com and rehabnet.com.
- "Residential addiction treatment near Nashville" omits it; Freeman, APEX and Tulip Hill are cited from their own residential pages.
- Google AI Overviews cite the domain for 417 keywords, the top 50 all blog posts ("12 steps", "barbiturates"), zero program or admissions pages.
- FAQPage schema only on the detox page and the admissions FAQ (1 of 30 program pages); homepage MedicalOrganization schema has no telephone, address or sameAs. robots.txt allows every AI citation bot.

**Why it costs calls**
- Rehab research increasingly starts in AI tools; the cited directory gets the call and tells the billing-complaint story.

**Fix**
- FAQPage answer blocks on residential, insurance, admissions and location pages (cost, length of stay, coverage, what to bring).
- Complete the MedicalOrganization schema; add an outcomes/alumni page engines can cite for "reviews".

**Check first**
- Search Console: brand-query trend (AI exposure shows up as brand searches).
- Call tracking: add "ChatGPT/AI" to "how did you hear about us"; check server logs for OAI-SearchBot, PerplexityBot and ChatGPT-User.

### 4. Thin trust signals on the pages where health decisions happen

**Health pages rarely show who wrote or reviewed them.**

**Evidence**
- 2 of 32 program/blog pages show a medical reviewer or credentialed byline.
- Joint Commission appears on inner pages but not the homepage; no LegitScript mention.
- Backlinks fell from 3,621 to 3,042 in 12 months (944 referring domains, spam score 41, largest referrer a directory).

**Why it costs calls**
- Google's health-page quality signals, AI engines and families all weigh visible expertise and accreditation.

**Fix**
- "Medically reviewed by <name, credentials>" with bios on every program and blog page.
- Joint Commission and LegitScript seals in the footer; clinical team page with Person schema.

**Check first**
- Search Console: clicks for /resources/blog/ vs /treatment/ around the last two core updates.
- Call tracking: calls starting on blog vs program pages.

### 5. Technical SEO: dead sitemap URLs, thin archives, phone variants, 4-7 s page responses

**The base is sound, but small leaks add up.**

**Evidence**
- Sitemap lists 3,234 URLs, ~1,100 of them image attachments; 23 of the first 150 fetched were 404.
- Tag and member-category archives (49-133 words) are indexable.
- Six tel: numbers on site plus different numbers on GBP, Facebook, NAATP and the ads microsite; uncached blog pages take 4-7 s.
- OpenSEO (120 pages) found no critical issues: the problems are strategic, not technical.

**Why it costs calls**
- Low direct cost: wasted crawl budget, weaker NAP matching for #1, a slow phone number on mobile.

**Fix**
- Sitemap from indexable pages only; noindex tag/member-category archives.
- One canonical NAP with dynamic number insertion; full-page caching/CDN.

**Check first**
- Search Console: Pages ("Not found", "Crawled, currently not indexed"), Sitemaps, Core Web Vitals.
- Call tracking: calls per number.

## Backlinks and domain authority

- DataForSEO domain rank 44; 4,810 backlinks from 944 referring domains.
- 12-month trend: backlinks 3,621 (Oct 2025) to 3,042 (Sep 2026), -16%; referring domains 924 to 894.
- Spam score 41 for the domain (13 for its backlinks).
- Top referrers are directories: addictiontreatments101.com (1,375 links), rehabconnectusa.com, alcoholrehabus.org, recovery.com. Few hospital, university or news links.
Competitor comparison (DataForSEO rank and referring domains):

| Domain | DataForSEO rank | Referring domains |
|---|---|---|
| cumberlandheights.org | 44 | 944 |
| recoveryranch.com | 40 | 3,837 |
| southeastaddictiontn.com | 36 | 2,570 |
| nashvilleaddictionrecovery.com | 34 | 2,471 |
| liveagaindetox.com | 34 | 2,429 |
| thenextdoorrecovery.org | 25 | 150 |

Cumberland Heights has the highest rank of the six, but four of the five competitors have 2.6 to 4 times as many referring domains. Monthly new/lost figures (+334 new, -309 lost) disagree with the 12-month drop, so the decline needs confirming in Search Console.

**Fix**
- Earn local links (hospitals, universities, county resources, Nashville news) pointed at program and city pages.

**Check first**
- Search Console Links report: top linking sites and target pages; whether referring domains keep dropping.

## On-page optimization

| Page | Title (verbatim) | Service + place? | Meta desc. length | H1 | Words | FAQ | Schema beyond Organization |
|---|---|---|---|---|---|---|---|
| / | Home - Cumberland Heights | No | 223 | 1 | 2,271 | No | MedicalOrganization, MedicalClinic, MedicalTherapy |
| /treatment/residential-care/ | Residential Care - Cumberland Heights | No | 411 | 1 | 801 | No | None |
| /treatment/drug-and-alcohol-detox/ | Drug & Alcohol Detox - Cumberland Heights | No | 360 | 1 | 1,744 | Yes | FAQPage |
| /admissions/insurance-and-finances/ | Insurance and Finances - Cumberland Heights | No | 360 | 1 | 657 | No | None |
| /locations/river-road/ | River Road - Cumberland Heights | No | 374 | 1 | 765 | No | None |

**Title rewrites**
- Home: "Cumberland Heights | Alcohol & Drug Rehab in Nashville, TN (since 1966)"
- Residential: "Residential Rehab in Nashville, TN | Cumberland Heights"
- Detox: "Drug & Alcohol Detox in Nashville, TN | Cumberland Heights"
- Insurance: "Rehab Insurance & Costs in Nashville, TN | Cumberland Heights"
- River Road: "Residential Rehab Campus in Nashville, TN | Cumberland Heights"

**Three on-page fixes**
- Cut meta descriptions (223-411 characters) to one sentence: program, Nashville, 24/7 phone, Joint Commission.
- Add a 4-6 question FAQ with FAQPage schema to residential, insurance and River Road.
- Add MedicalClinic schema with telephone, address and sameAs to program and River Road pages; fix the invalid JSON-LD block on the homepage.

**Site audit.** OpenSEO found no critical issues in 120 pages. Warnings: 8 missing H1s (event pages), 4 duplicate event titles, and missing alt text (17 of 69 homepage images).

## GEO: brand mentions in AI answers vs competitors

| Query (engine) | Mentioned | Cited | Who was cited |
|---|---|---|---|
| Best alcohol rehab in Nashville (Perplexity) | Yes, first | No | Freeman, startyourrecovery.org, rehab.com |
| Rehabs accepting BCBS or Aetna (Perplexity) | Yes | No | rehabseekers.com, startyourrecovery.org, recovery.com |
| Residential treatment near Nashville (Perplexity) | No | No | Freeman, Tulip Hill, Renaissance, APEX, tndetoxcenter.com |
| Cumberland Heights reviews (Perplexity) | Yes | No | yelp.com, bbb.org, indeed.com, rehabseekers.com |
| Is Cumberland Heights good, what insurance (Perplexity) | Yes | Yes | cumberlandheights.org, a separate cumberlandheights.com, rehab.com |
| alcohol / drug rehab nashville (Google) | Organic only | No | No AI Overview; pack: Recovery Unplugged, Southeast Addiction |
| cumberland heights (Google) | Yes | Yes | AI Overview; facebook.com, recovery.com, naatp.org |

Third-party listings on the brand SERP carry four other phone numbers.

Share of voice on 8 non-brand Nashville queries (Perplexity, 21 Oct 2026; mentioned / own domain cited / average first-mention position):

| Brand | Mentioned (of 8) | Own domain cited (of 8) | Own-domain citation URLs | Avg first-mention position |
|---|---|---|---|---|
| Freeman Recovery Center | 6 | 7 | 27 | 2.33 |
| APEX Recovery | 3 | 5 | 6 | 2.0 |
| Live Again Detox | 3 | 2 | 3 | 2.0 |
| **Cumberland Heights** | **2** | **0** | **0** | **1.0** |
| The Next Door Recovery | 2 | 0 | 0 | 2.5 |
| Southeast Addiction Center | 1 | 1 | 1 | 1.0 |
| Tulip Hill | 1 | 3 | 3 | 4.0 |
| Recovery Unplugged | 0 | 0 | 0 | n/a |
| The Ranch Tennessee / Recovery Ranch | 0 | 0 | 0 | n/a |
| Brentwood Springs Detox | 0 | 0 | 0 | n/a |

Freeman Recovery Center is cited from its own site in 7 of 8 answers, including its insurance and cost pages. Cumberland Heights is mentioned in 2 of 8 (named first both times, but supported by directory pages) and cited from its own domain in none. The most-cited third-party domains are psychologytoday.com (6 queries), recovery.com (4) and startyourrecovery.org (3). One run on one engine: a snapshot, not a trend.

**Fix**
- Citable residential, insurance and outcomes pages.
- Correct NAP and program data on the cited directories; resolve cumberlandheights.com.

**Check first**
- Search Console: brand impressions monthly; non-brand impressions on residential-care.
- Call tracking: calls to the directory numbers.

## Topical authority vs competitors

Method: the top 200 ranking keywords (by traffic and by volume) for cumberlandheights.org and six competitors from DataForSEO, clustered into 17 topics by keyword pattern. A topic score of 100 means the domain has the most top-10 keywords in that topic among the seven. Full matrix and keyword gap in `out/cumberlandheights.org/topical_authority.md`.

**Where the site is strong and weak**

- Strongest: 12-step and recovery education (100, 21 top-10 keywords), benzos and barbiturates (100, but all 7 are "barbiturate" definition queries), local intent (53, 16 top-10 keywords, tied with The Ranch).
- Weakest against the best competitor: detox (score 5; 1 top-10 keyword vs 21 for Live Again Detox), alcohol (5; 1 vs 20 for Recovery Unplugged), mental health and dual diagnosis (22; 4 vs 18 for The Ranch).
- Who owns what: Recovery Unplugged owns alcohol, stimulants, benzos and cannabis; Southeast Addiction owns opioids; Live Again owns detox, family and local; APEX owns residential, outpatient, insurance and professionals; The Ranch owns mental health and 12-step. No domain has a top-10 keyword for adolescents, which Cumberland Heights treats (ARCH Academy) and could own.

**Intent mix of ranking traffic**

| Domain | Informational | Commercial / local | Brand |
|---|---|---|---|
| cumberlandheights.org | 75.5% | 13% | 11.5% |
| apex.rehab | 46.2% | 53.8% | n/a |
| liveagaindetox.com | 13.5% | 86.5% | n/a |
| nashvilleaddictionrecovery.com | 2.2% | 97.8% | n/a |

12-step plus mental-health blog topics carry 63 percent of the site's sampled traffic; the competitors that win calls rank almost only for commercial and local intent.

**Keyword gap (top 20 for two or more competitors, absent from the site's top 200)**

| Keyword | Volume / mo | Topic | Best competitor |
|---|---|---|---|
| detox nashville | 720 | detox, local | liveagaindetox.com |
| detox nashville tn | 720 | detox, local | liveagaindetox.com |
| nashville detox | 720 | detox, local | liveagaindetox.com |
| tennessee detox center | 480 | detox | tndetoxcenter.com / liveagaindetox.com |
| treatment center nashville | 110 | local | southeastaddictiontn.com |

The list is short because each competitor's top 200 barely overlaps the others', and only the site's top 200 of 5,107 keywords were checked; confirm each gap in Search Console before building.

**Fix**

- A detox hub: one page for Nashville detox (the 2,160 searches a month above), with alcohol, opioid and benzo detox sub-pages, each with cost, length, what to bring and insurance.
- An alcohol-rehab hub and a mental-health/dual-diagnosis hub, the two topics where the gap to the leader is largest.
- An adolescent treatment hub around ARCH Academy, an open topic no competitor ranks for.
- Keep the 12-step and recovery-education content, but link every post to the matching hub.

**Check first**

- Search Console: queries grouped by these topics (regex filters for detox, alcohol, mental health, teen/adolescent) with impressions at positions 4-20; those are the pages to build or expand first.
- Call tracking: calls from the few detox and alcohol pages that exist today, to size what a hub is worth.

## Competitor on-page strategies and entity scores

Method: fetched the six pages that win the Nashville rehab SERPs and the site's four money pages, extracted the same attributes from each, and scored "entity" signals (schema completeness, NAP, sameAs, FAQ, accreditation, local density) out of 100. Full detail in `out/cumberlandheights.org/competitor_pages.md`.

**Entity scores (out of 100)**

| Page | Score |
|---|---|
| apex.rehab/tennessee/nashville/ | 65 |
| recoveryunplugged.com/location/drug-rehab-in-nashville/ | 65 |
| liveagaindetox.com | 60 |
| recoveryranch.com | 45 |
| southeastaddictiontn.com | 40 |
| thenextdoorrecovery.org | 25 |
| **cumberlandheights.org (home)** | **60** |
| cumberlandheights.org/treatment/drug-and-alcohol-detox/ | 30 |
| cumberlandheights.org/admissions/insurance-and-finances/ | 25 |
| cumberlandheights.org/treatment/residential-care/ | 20 |

Competitor average 50, Cumberland Heights money-page average 34. The homepage holds its own; the program and insurance pages are where the entity signals disappear.

**What each winner does**

- APEX: a dedicated `/tennessee/nashville/` page, title and H1 "Drug and Alcohol Rehab in Nashville, TN", 7,239 words across 17 H2s, "Nashville" 173 times, 11 insurers named with 12 logos, Joint Commission named, tel + form + verify-insurance, 24/7 stated.
- Recovery Unplugged: `/location/drug-rehab-in-nashville/`, aggregateRating 5.0 from 610 reviews in schema, local schema type, locations and programs in the nav, 24/7, verify-insurance.
- Live Again Detox: homepage as the Nashville page, "Nashville" 90 times, 7 insurers named, Joint Commission and LegitScript named, local schema, 24/7.
- Southeast Addiction: homepage as the Nashville page, 3 testimonial blocks, 9 insurer logos, 24/7, form.
- The Ranch: 16 insurer logos, 24/7, but thin (851 words) and only two "Nashville" mentions; it ranks on authority (3,837 referring domains).

**Copy first, ordered by how many competitors do it and how cheap it is**

1. State 24/7 on every money page (6 of 6 competitors; 1 of 4 site pages).
2. Meta descriptions of 70-160 characters with a call to action (5 of 6; 0 of 4).
3. Insurer logos with alt text on the insurance and program pages (5 of 6; 3 of 4).
4. Say "Nashville" in body copy, at least 5 times on each money page (5 of 6; 0 of 4).
5. A "Verify insurance" button on every money page (5 of 6; 3 of 4).
6. sameAs with 3+ profiles in the schema (4 of 6; 1 of 4), then aggregateRating from Google reviews, which only Recovery Unplugged does.

**Check first**

- Search Console: impressions and CTR for /treatment/ and /admissions/ pages on queries containing "nashville", before and after the copy and schema changes.
- Call tracking: calls per landing page for those URLs, to see whether the entity and CTA changes move calls, not just rankings.

## Link building and mention opportunities (competitor link gap)

Method: pulled the dofollow referring domains of five Nashville competitors and of cumberlandheights.org from DataForSEO (570 of the site's 575 dofollow domains covered), kept domains that link to a competitor but not to the site, classified them, and down-weighted pay-to-play directories. Full table in `out/cumberlandheights.org/link_opportunities.md`.

**What the gap looks like**

- 567 referring domains link to at least one competitor and not to Cumberland Heights: 325 blog/other, 71 associations, 67 news/media, 54 directories, 27 health systems, 14 education, 9 government. 24 of them link to two or more competitors.
- Competitors earn these in three repeatable ways: expert quotes in national media (Southeast Addiction's clinical director on scarymommy.com and huffpost.com; goodmenproject.com links three competitors), resource-page listings at universities (preventhazing.arizona.edu, journalism.columbia.edu, blogs.oregonstate.edu, sites.psu.edu) and press-release distribution (The Ranch via globenewswire.com). Live Again Detox has the Nashville Chamber (web.nashvillechamber.com) link; Cumberland Heights does not.
- Directory and lead-gen listings dominate the site's own profile (addictiontreatments101.com alone is 1,375 links), so the gap is in earned media, education and local institutions, not in more directories.

**Where the AI engines get their facts, and whether the site is listed there**

| Domain | Cited in AI answers (of 18) | Site has a backlink | Action |
|---|---|---|---|
| psychologytoday.com | 9 | no | Claim and complete the treatment-center listing: every insurer, level of care, photos |
| startyourrecovery.org | 7 | yes | Complete the listing, fix NAP, collect reviews |
| recovery.com | 6 | yes | Same |
| rehab.com | 5 | no | Claim the listing |
| bbb.org | 3 | no | Accredit the profile, answer complaints publicly (the billing complaints surface in AI answers) |
| yelp.com | 3 | no | Claim, fix categories, reply to every review, ask alumni for reviews |

**Fix: first ten outreach targets, in order**

1. Psychology Today listing, complete with insurers and photos (free, cited most).
2. BBB accreditation and public complaint responses.
3. Yelp and rehab.com claims with NAP matching the Google Business Profile.
4. Nashville Area Chamber of Commerce membership listing.
5. Collegiate-recovery resource pages at Vanderbilt, Belmont, MTSU, Lipscomb and TSU (the .edu pattern competitors already use).
6. Metro Nashville and Davidson County behavioral-health resource lists (.gov).
7. Hospital and health-system referral pages (Vanderbilt, Ascension Saint Thomas, TriStar).
8. Expert-quote pitches to the outlets that quoted competitors (Good Men Project, Scary Mommy, HuffPost) on family, relapse and holiday topics.
9. A press release for the 60th anniversary in 2026 and for outcomes data, distributed and pitched to Nashville news (newschannel5.com already links once).
10. Alumni and family-program event pages on partner sites (churches, recovery community organizations).

**Check first**

- Search Console Links report: top linking sites and top linked pages, to confirm which of the 570 domains Google actually credits.
- Call tracking by referral source: do calls from Psychology Today and directory referrals convert better than organic? That sets the priority between claims and earned media.

## Running this continuously

`schedule/` turns the audit into an unattended job: `run_sites.sh` audits every site in `sites.txt`, keeps a dated snapshot per run, and `diff_runs.py` reports new, resolved and changed findings. A launchd plist (macOS) and a systemd timer or crontab (Linux VPS) run it daily. Each run costs a few hundred DataForSEO credits unless market data is skipped.

## Limits

No GSC, analytics or call data, so impact is estimated from page intent and market data. Core Web Vitals not measured (PageSpeed quota exhausted; 8 of 20 OpenSEO Lighthouse runs failed). AI answers are a one-day snapshot of 15 queries (5 in the first pass, 10 in the share-of-voice run). The ~48K estimated monthly organic visits are mostly informational blog traffic ("12 step program aa" alone is ~4.8K); the pages that drive calls earn a small share.
