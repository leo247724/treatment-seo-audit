"""Audit checks. Each returns a list of Finding. Severity 1-5, intent weight from the pages hit."""
import re
from collections import Counter, defaultdict
from .models import Finding, Page

LOCAL_SCHEMA = {"LocalBusiness", "MedicalClinic", "MedicalBusiness", "Hospital", "MedicalOrganization",
                "Physician", "Place", "HealthAndBeautyBusiness", "Organization"}


def html_pages(site) -> list[Page]:
    return [p for p in site["pages"].values() if p.status == 200 and p.is_html and not p.error]


def indexable(site) -> list[Page]:
    return [p for p in html_pages(site) if p.indexable]


def hi(pages, min_w=4):
    return [p for p in pages if p.intent_weight >= min_w]


def urls(pages, n=8):
    return [p.final_url or p.url for p in pages[:n]]


def max_weight(pages, default=2):
    return max((p.intent_weight for p in pages), default=default)


def _f(**kw) -> Finding:
    kw.setdefault("confidence", "medium")
    kw.setdefault("page_count", len(kw.get("pages", [])))
    return Finding(**kw)


# ----------------------------------------------------------------- technical
def check_robots_sitemap(site):
    out = []
    pages = site["pages"]
    home = pages.get(site.get("start_url")) or next((p for p in pages.values() if p.page_type == "home"), None)
    if site["robots_status"] != 200:
        out.append(_f(id="robots_missing", category="technical", title="robots.txt missing or unreachable",
                      severity=2, intent_weight=2, pages=[site["start_url"] + "robots.txt"],
                      evidence=[f"HTTP {site['robots_status']} for /robots.txt"],
                      why_it_matters="Crawlers fall back to defaults; sitemap discovery and AI-bot policy are undefined.",
                      fix="Publish robots.txt with a Sitemap: line and explicit bot rules.",
                      check_first="GSC > Settings > robots.txt report."))
    if home and home.error == "blocked by robots.txt":
        out.append(_f(id="robots_blocks_home", category="technical", title="robots.txt blocks the homepage",
                      severity=5, intent_weight=5, pages=[site["start_url"]], evidence=["Disallow matches /"],
                      why_it_matters="Nothing can rank.", fix="Remove the Disallow rule.", check_first="GSC Pages report."))
    if not site["sitemap_sources"]:
        out.append(_f(id="sitemap_missing", category="technical", title="No XML sitemap found",
                      severity=3, intent_weight=3, pages=[], page_count=0,
                      evidence=["Checked robots.txt Sitemap: lines, /sitemap.xml, /sitemap_index.xml, /wp-sitemap.xml"]
                               + site["sitemap_errors"][:5],
                      why_it_matters="New program/location pages get discovered late or never; crawl budget goes to blog archives.",
                      fix="Generate an XML sitemap (Yoast/RankMath or framework plugin) and reference it in robots.txt.",
                      check_first="GSC > Sitemaps: is one submitted and how many URLs are 'discovered - not indexed'?"))
    else:
        bad = [p for p in pages.values() if p.in_sitemap and p.status and p.status != 200]
        if bad:
            out.append(_f(id="sitemap_bad_urls", category="technical", title="Sitemap lists URLs that do not return 200",
                          severity=3, intent_weight=max_weight(bad), pages=urls(bad),
                          page_count=len(bad), evidence=[f"{p.url} -> HTTP {p.status}" for p in bad[:8]],
                          why_it_matters="Google trusts the sitemap less and wastes crawl budget on dead URLs.",
                          fix="Regenerate the sitemap from live, indexable URLs only.",
                          check_first="GSC > Pages > 'Not found (404)' and 'Redirect error' filtered to sitemap URLs."))
        noidx = [p for p in pages.values() if p.in_sitemap and p.noindex]
        if noidx:
            out.append(_f(id="sitemap_noindex", category="technical", title="Sitemap includes noindex pages",
                          severity=2, intent_weight=max_weight(noidx), pages=urls(noidx), page_count=len(noidx),
                          evidence=[p.url for p in noidx[:8]],
                          why_it_matters="Contradictory signals; Google may ignore the sitemap.",
                          fix="Exclude noindex URLs from the sitemap.", check_first="GSC Pages > 'Excluded by noindex tag'."))
        missing = [p for p in indexable(site) if not p.in_sitemap and p.intent_weight >= 4]
        if missing:
            out.append(_f(id="sitemap_coverage", category="technical", title="High-intent pages missing from the sitemap",
                          severity=2, intent_weight=max_weight(missing), pages=urls(missing), page_count=len(missing),
                          evidence=[f"{len(missing)} crawled program/location/admissions pages are not in the sitemap"],
                          why_it_matters="Pages that drive calls depend on internal links alone for discovery.",
                          fix="Include every indexable program, location and admissions URL.",
                          check_first="GSC URL Inspection on 3 of these: 'URL is not on Google'?"))
    return out


def check_links_and_redirects(site):
    out = []
    pages = site["pages"]
    sources = defaultdict(list)
    for p in html_pages(site):
        for l in p.internal_links:
            sources[l].append(p)
    broken = [p for p in pages.values() if p.status in (404, 410) or p.status >= 500]
    if broken:
        weight = max(max_weight(broken), max((max_weight(sources[p.url]) for p in broken if sources[p.url]), default=2))
        ev = [f"{p.url} -> HTTP {p.status} (linked from {len(sources[p.url])} pages, e.g. {sources[p.url][0].url if sources[p.url] else 'sitemap'})"
              for p in broken[:8]]
        out.append(_f(id="broken_links", category="technical", title="Internal links to broken (4xx/5xx) pages",
                      severity=4 if weight >= 4 else 2, intent_weight=weight, pages=urls(broken), page_count=len(broken),
                      evidence=ev, why_it_matters="A prospect clicking a dead 'Admissions' or program link leaves; link equity is lost.",
                      fix="Redirect or fix the targets, then update the source links.",
                      check_first="GSC > Pages > Not found (404): which have impressions? Call tracking: calls from these landing URLs before they broke."))
    chains = [p for p in pages.values() if p.redirects >= 2 and p.url != site.get("start_url")]
    redirected_links = [u for u, src in sources.items() if u in pages and pages[u].redirects >= 1 and pages[u].status == 200]
    if chains or redirected_links:
        ev = [f"{p.url} -> {p.redirects} hops -> {p.final_url}" for p in chains[:5]]
        ev += [f"{len(redirected_links)} internal links point at redirecting URLs (e.g. {redirected_links[0]})"] if redirected_links else []
        out.append(_f(id="redirects", category="technical", title="Redirect chains and internal links to redirecting URLs",
                      severity=2, intent_weight=max_weight([pages[u] for u in redirected_links] + chains),
                      pages=redirected_links[:8], page_count=len(redirected_links) + len(chains), evidence=ev,
                      why_it_matters="Each hop adds latency on mobile and leaks ranking signals.",
                      fix="Update internal links to final URLs; collapse chains to a single 301.",
                      check_first="GSC crawl stats: redirect share of crawl requests."))
    return out


def check_indexability(site):
    out = []
    noidx = [p for p in html_pages(site) if p.noindex and p.intent_weight >= 4]
    if noidx:
        out.append(_f(id="noindex_high_intent", category="technical", title="noindex on program/location/admissions pages",
                      severity=5, intent_weight=max_weight(noidx), pages=urls(noidx), page_count=len(noidx),
                      evidence=[f"{p.url}: robots='{p.meta_robots or p.x_robots}'" for p in noidx[:8]],
                      why_it_matters="These pages cannot rank at all, so every call they would have generated goes to a competitor.",
                      fix="Remove noindex unless the page is a true duplicate.",
                      check_first="GSC Pages > 'Excluded by noindex tag' and URL Inspection history."))
    canon = [p for p in indexable(site) if p.canonical and p.canonical != (p.final_url or p.url) and p.intent_weight >= 4]
    if canon:
        out.append(_f(id="canonical_away", category="technical", title="High-intent pages canonicalise to a different URL",
                      severity=4, intent_weight=max_weight(canon), pages=urls(canon), page_count=len(canon),
                      evidence=[f"{p.final_url} -> canonical {p.canonical}" for p in canon[:8]],
                      why_it_matters="Google consolidates the page into the canonical target; the page itself stops ranking.",
                      fix="Self-referencing canonicals unless the page is a deliberate duplicate.",
                      check_first="GSC URL Inspection: 'Google-selected canonical' vs user-declared."))
    nocanon = [p for p in indexable(site) if not p.canonical]
    if nocanon and len(nocanon) > len(indexable(site)) * 0.3:
        out.append(_f(id="canonical_missing", category="technical", title="Missing canonical tags", severity=1,
                      intent_weight=max_weight(nocanon), pages=urls(nocanon), page_count=len(nocanon),
                      evidence=[f"{len(nocanon)} of {len(indexable(site))} indexable pages lack rel=canonical"],
                      why_it_matters="UTM/tracking variants and www/non-www copies can split signals.",
                      fix="Emit self-referencing canonicals site-wide.", check_first="GSC Pages > 'Duplicate without user-selected canonical'."))
    return out


def check_titles_meta(site):
    out = []
    idx = indexable(site)
    missing_t = [p for p in idx if not p.title.strip()]
    titles = Counter(p.title.strip().lower() for p in idx if p.title.strip())
    dup_t = [p for p in idx if titles[p.title.strip().lower()] > 1]
    if missing_t or dup_t:
        out.append(_f(id="titles_missing_dup", category="content", title="Missing or duplicate title tags",
                      severity=3, intent_weight=max_weight(missing_t + dup_t), pages=urls(missing_t + dup_t),
                      page_count=len(missing_t) + len(dup_t),
                      evidence=[f"{len(missing_t)} missing"] + [f"'{t}' used on {c} pages" for t, c in titles.most_common(5) if c > 1],
                      why_it_matters="The title is the ad headline in search; duplicates make program pages compete with each other.",
                      fix="Unique titles: '<Program> in <City>, <ST> | <Brand>'.", check_first="GSC Performance: pages with high impressions and CTR under 2%."))
    long_t = [p for p in idx if len(p.title) > 65]
    short_t = [p for p in idx if 0 < len(p.title) < 25]
    if long_t or short_t:
        out.append(_f(id="title_length", category="content", title="Title tags too long or too short", severity=1,
                      intent_weight=max_weight(long_t + short_t), pages=urls(long_t + short_t),
                      page_count=len(long_t) + len(short_t),
                      evidence=[f"{len(long_t)} over 65 chars, {len(short_t)} under 25 chars"] + [f"{len(p.title)} chars: {p.title[:80]}" for p in long_t[:3]],
                      why_it_matters="Truncated titles hide the location or program name in results.",
                      fix="Keep the program + city in the first 55 characters.", check_first="GSC CTR by page vs. position."))
    missing_md = [p for p in idx if not p.meta_description.strip()]
    if missing_md:
        out.append(_f(id="meta_desc_missing", category="content", title="Missing meta descriptions", severity=2,
                      intent_weight=max_weight(missing_md), pages=urls(missing_md), page_count=len(missing_md),
                      evidence=[f"{len(missing_md)} of {len(idx)} indexable pages"],
                      why_it_matters="Google writes its own snippet, usually without the phone number, insurance or '24/7' hook.",
                      fix="Write descriptions that state program, location, insurance accepted and a call prompt.",
                      check_first="GSC: CTR on high-impression program pages."))
    no_h1 = [p for p in idx if not p.h1s]
    multi_h1 = [p for p in idx if len(p.h1s) > 1]
    if no_h1 or multi_h1:
        out.append(_f(id="h1", category="content", title="Missing or multiple H1 headings", severity=2,
                      intent_weight=max_weight(no_h1 + multi_h1), pages=urls(no_h1 + multi_h1),
                      page_count=len(no_h1) + len(multi_h1),
                      evidence=[f"{len(no_h1)} pages with no H1, {len(multi_h1)} with more than one"],
                      why_it_matters="Weak topical signal for program/location pages.",
                      fix="One H1 per page naming the service and place.", check_first="None needed; template fix."))
    return out


def check_thin_content(site):
    thin = [p for p in indexable(site) if p.intent_weight >= 4 and p.page_type != "home" and p.main_word_count < 300]
    if not thin:
        return []
    return [_f(id="thin_high_intent", category="content", title="Thin program/location/admissions pages (under 300 words)",
               severity=3, intent_weight=max_weight(thin), pages=urls(thin), page_count=len(thin),
               evidence=[f"{p.final_url}: {p.main_word_count} words" for p in sorted(thin, key=lambda p: p.main_word_count)[:8]],
               why_it_matters="Pages that cannot answer 'what happens, who is it for, what does it cost, is it covered' rarely rank for city + program queries and are rarely quoted by AI engines.",
               fix="Expand each to cover program description, levels of care, insurance, admission steps, staff, FAQ.",
               check_first="GSC: impressions vs clicks per page; which program queries do these pages appear for at position 8-20?")]


def check_mobile_and_security(site):
    out = []
    nov = [p for p in indexable(site) if not p.has_viewport]
    if nov:
        out.append(_f(id="viewport_missing", category="technical", title="Pages without a mobile viewport meta tag", severity=4,
                      intent_weight=max_weight(nov), pages=urls(nov), page_count=len(nov),
                      evidence=[f"{len(nov)} indexable pages"],
                      why_it_matters="Most addiction searches happen on phones; non-responsive pages lose the click-to-call moment.",
                      fix="Add <meta name=viewport content='width=device-width, initial-scale=1'>.",
                      check_first="GSC Performance filtered to mobile: CTR and position vs desktop."))
    mixed = [p for p in indexable(site) if p.mixed_content]
    if mixed:
        out.append(_f(id="mixed_content", category="technical", title="Mixed content (http:// assets on https pages)", severity=2,
                      intent_weight=max_weight(mixed), pages=urls(mixed), page_count=len(mixed),
                      evidence=[f"{p.final_url}: {p.mixed_content} http assets" for p in mixed[:5]],
                      why_it_matters="Browser warnings on a page asking for health information kill trust.",
                      fix="Rewrite asset URLs to https.", check_first="None."))
    if site.get("home_final_url", "").startswith("http://"):
        out.append(_f(id="no_https", category="technical", title="Homepage served over HTTP", severity=5, intent_weight=5,
                      pages=[site["home_final_url"]], evidence=[site["home_final_url"]],
                      why_it_matters="'Not secure' warning on a healthcare site.", fix="Force HTTPS with a 301.", check_first="None."))
    return out


# ----------------------------------------------------------------- conversion
def check_click_to_call(site):
    out = []
    idx = indexable(site)
    no_tel = [p for p in idx if not p.tel_links]
    no_tel_hi = hi(no_tel)
    if no_tel:
        phone_text_only = [p for p in no_tel if p.phones_in_text]
        out.append(_f(id="no_tel_link", category="conversion", title="Pages with no click-to-call (tel:) link",
                      severity=5 if no_tel_hi else 3, intent_weight=max_weight(no_tel), pages=urls(no_tel_hi or no_tel),
                      page_count=len(no_tel),
                      evidence=[f"{len(no_tel)} of {len(idx)} indexable pages have no tel: link; {len(no_tel_hi)} are program/location/admissions pages",
                                f"{len(phone_text_only)} of them show a phone number as plain text only"]
                               + [p.final_url for p in no_tel_hi[:6]],
                      why_it_matters="On mobile a tappable number is the whole conversion. Plain-text numbers mean copy-paste or abandonment, and call tracking cannot attribute the call.",
                      fix="Make every phone number an <a href='tel:'> link, in the header and in each page's CTA block.",
                      check_first="Call tracking: calls by landing page for these URLs vs pages that have tel links. GSC: mobile share of clicks to them.",
                      confidence="high"))
    no_header = [p for p in idx if p.tel_links and not p.header_has_tel]
    if no_header and len(no_header) > len(idx) * 0.2:
        out.append(_f(id="tel_not_in_header", category="conversion", title="Phone number not in the site header",
                      severity=3, intent_weight=max_weight(no_header), pages=urls(hi(no_header) or no_header),
                      page_count=len(no_header),
                      evidence=[f"{len(no_header)} pages have a tel link only below the header region"],
                      why_it_matters="Visitors in crisis do not scroll. A sticky header number is the highest-converting element on treatment sites.",
                      fix="Put the admissions number (tel: link) in the persistent header, plus a sticky mobile call bar.",
                      check_first="Call tracking: share of calls from the header number vs body CTAs (needs separate swap numbers).",
                      confidence="medium"))
    return out


def check_phone_consistency(site):
    nums = Counter()
    where = defaultdict(set)
    for p in html_pages(site):
        for n in p.tel_links:
            n = n[-10:]
            nums[n] += 1
            where[n].add(p.final_url or p.url)
    if len(nums) <= 2:
        return []
    return [_f(id="phone_variants", category="local", title=f"{len(nums)} different phone numbers in tel: links",
               severity=2, intent_weight=3, pages=[], page_count=len(nums),
               evidence=[f"{n[:3]}-{n[3:6]}-{n[6:]}: on {c} pages (e.g. {next(iter(where[n]))})" for n, c in nums.most_common(8)],
               why_it_matters="Multiple numbers can be legitimate call-tracking swaps, but if they are hard-coded they fragment NAP consistency and Google Business Profile matching.",
               fix="One primary admissions number in schema and footer; use dynamic number insertion (CallRail/CTM) for tracking rather than hard-coded variants.",
               check_first="Call tracking: are these pool numbers? If any number is not in the tracking tool, find who owns it.",
               confidence="low")]


def check_admissions_path(site):
    out = []
    idx = indexable(site)
    def find(*keys):
        return [p for p in idx if p.page_type not in ("content", "archive")
                and any(k in (p.final_url + " " + p.title).lower() for k in keys)]
    insurance = find("insurance", "verify", "coverage", "payment", "cost", "pricing", "financ")
    admissions = find("admission", "get-help", "get-started", "intake", "what-to-expect")
    contact = find("contact")
    home = next((p for p in idx if p.page_type == "home"), None)
    if not insurance:
        out.append(_f(id="no_insurance_page", category="conversion", title="No insurance / cost page found", severity=5, intent_weight=5,
                      pages=[], page_count=0, evidence=["No crawled URL or title contains insurance/verify/coverage/cost/pricing"],
                      why_it_matters="'Does X take my insurance' is the first question every family asks; without a page you lose the query and the call.",
                      fix="Create /insurance (payers, in/out-of-network, verification form, self-pay) and link it from header and every program page.",
                      check_first="GSC: queries containing 'insurance', 'aetna', 'bcbs', 'cost' and which pages currently rank for them."))
    else:
        payers = [p for p in insurance if p.mentions.get("insurance_payers")]
        if not payers:
            out.append(_f(id="insurance_no_payers", category="conversion", title="Insurance page names no insurers", severity=4, intent_weight=5,
                          pages=urls(insurance), page_count=len(insurance),
                          evidence=[f"{p.final_url}: no payer names (Aetna, BCBS, Cigna, UHC, TRICARE, Medicaid...) found" for p in insurance[:4]],
                          why_it_matters="Pages that name payers rank for '<rehab> that takes <insurer> <city>' queries, which convert at the highest rate.",
                          fix="List accepted payers with logos and a 'verify your benefits' form; one paragraph per major payer.",
                          check_first="GSC: impressions for '[insurer] rehab' queries. Call tracking: how many callers ask about coverage first?"))
    verify_any = any(p.mentions.get("verify_insurance") for p in idx)
    if insurance and not verify_any:
        out.append(_f(id="no_verify_cta", category="conversion", title="No 'verify your insurance' call-to-action anywhere", severity=3, intent_weight=5,
                      pages=urls(insurance), page_count=len(insurance),
                      evidence=["No page text matches 'verify (your) insurance/benefits/coverage'"],
                      why_it_matters="A verification form captures families who are not ready to call; it is the second conversion path.",
                      fix="Add a short HIPAA-compliant verification form (name, phone, insurer, member ID optional) on the insurance page and as a site-wide CTA.",
                      check_first="Call tracking + form submissions: current form-to-call ratio."))
    if not admissions:
        out.append(_f(id="no_admissions_page", category="conversion", title="No admissions / what-to-expect page found", severity=4, intent_weight=5,
                      pages=[], page_count=0, evidence=["No crawled URL/title contains admissions, get help, intake or what to expect"],
                      why_it_matters="Families need to know the steps before they call; the page also anchors 'admissions' and 'how to get into rehab' queries.",
                      fix="Create /admissions: steps, what to bring, who answers the phone, timing, insurance.",
                      check_first="GSC: queries with 'admission', 'how to get into'."))
    hi_pages = [home] + admissions + contact + insurance if home else admissions + contact + insurance
    hi_pages = [p for p in hi_pages if p]
    if hi_pages and not any(p.mentions.get("available_24_7") for p in hi_pages):
        out.append(_f(id="no_24_7", category="conversion", title="No '24/7' availability message on home/admissions/contact", severity=3, intent_weight=5,
                      pages=urls(hi_pages), page_count=len(hi_pages),
                      evidence=["No match for 24/7, 24 hours, around the clock, day or night on these pages"],
                      why_it_matters="Most crisis calls come at night and weekends; without the promise people call a competitor's '24/7 helpline' instead.",
                      fix="State the hours the phone is answered (or 24/7 if true) beside the number, header and footer.",
                      check_first="Call tracking: call volume by hour and answer rate after 6pm/weekends. If calls go to voicemail, fix answering before advertising 24/7.",
                      confidence="medium"))
    formless = [p for p in admissions + contact + insurance if p.forms == 0]
    if formless and len(formless) == len(admissions + contact + insurance):
        out.append(_f(id="no_forms", category="conversion", title="Admissions/contact/insurance pages have no form", severity=3, intent_weight=5,
                      pages=urls(formless), page_count=len(formless),
                      evidence=[p.final_url for p in formless[:6]],
                      why_it_matters="Phone-only conversion loses people who cannot talk privately at that moment.",
                      fix="Add a short, HIPAA-compliant callback form (no detailed health questions) to each.",
                      check_first="If forms exist but load via JS, this is a false positive: confirm in the browser.",
                      confidence="low"))
    return out


# ----------------------------------------------------------------- local
def local_pages(site):
    return [p for p in indexable(site) if p.page_type == "local" or (p.addresses and p.has_map)]


def check_location_pages(site):
    out = []
    locs = local_pages(site)
    if not locs:
        return [_f(id="no_location_pages", category="local", title="No dedicated location pages detected", severity=3, intent_weight=4,
                   pages=[], page_count=0,
                   evidence=["No crawled page has a /location-style URL or an address plus embedded map"],
                   why_it_matters="'rehab near me' and '<city> rehab' queries are won by per-facility pages tied to a Google Business Profile.",
                   fix="One page per facility: address, map, phone, hours, programs offered there, photos, staff, LocalBusiness schema.",
                   check_first="GSC: queries containing city names and 'near me'; GBP Insights for direction requests and calls.",
                   confidence="low")]
    no_schema = [p for p in locs if not (set(p.jsonld_types) & LOCAL_SCHEMA)]
    no_tel = [p for p in locs if not p.tel_links]
    no_addr = [p for p in locs if not p.addresses]
    no_map = [p for p in locs if not p.has_map]
    ev = [f"{len(locs)} location pages found",
          f"{len(no_schema)} without LocalBusiness/MedicalClinic schema",
          f"{len(no_tel)} without a tel: link", f"{len(no_addr)} without a street address in text",
          f"{len(no_map)} without an embedded map"]
    if no_schema or no_tel or no_addr:
        out.append(_f(id="location_pages_incomplete", category="local", title="Location pages missing NAP, tel link or local schema",
                      severity=4 if (no_tel or no_addr) else 3, intent_weight=4,
                      pages=urls(no_schema + no_tel + no_addr), page_count=len(set(no_schema + no_tel + no_addr)),
                      evidence=ev + [f"{p.final_url}: schema={p.jsonld_types or 'none'}, tel={'yes' if p.tel_links else 'no'}, addr={'yes' if p.addresses else 'no'}" for p in locs[:6]],
                      why_it_matters="Local pack rankings and 'near me' calls depend on consistent NAP and schema matching the Google Business Profile.",
                      fix="Add MedicalClinic/LocalBusiness JSON-LD (name, address, telephone, geo, openingHours, sameAs to GBP), a tel link and the written address to each location page.",
                      check_first="GBP Insights: calls and direction requests per location; GSC: clicks to each location URL for city queries."))
    return out


def check_org_schema(site):
    pages = site["pages"]
    home = next((p for p in html_pages(site) if p.page_type == "home"), None)
    if not home:
        return []
    org_types = {"Organization", "MedicalOrganization", "LocalBusiness", "MedicalClinic", "MedicalBusiness", "Hospital"}
    has_org = bool(set(home.jsonld_types) & org_types)
    raw = str(home.jsonld_raw)
    has_phone = '"telephone"' in raw
    has_addr = '"address"' in raw or '"PostalAddress"' in raw
    has_same = '"sameAs"' in raw
    if has_org and has_phone and has_addr and has_same:
        return []
    ev = [f"Homepage JSON-LD types: {home.jsonld_types or 'none'}",
          f"telephone: {'yes' if has_phone else 'no'}, address: {'yes' if has_addr else 'no'}, sameAs: {'yes' if has_same else 'no'}"]
    return [_f(id="org_schema", category="ai_visibility", title="Homepage lacks a complete Organization/MedicalOrganization schema",
               severity=3 if not has_org else 2, intent_weight=5, pages=[home.final_url], page_count=1, evidence=ev,
               why_it_matters="Entity data (name, phone, address, sameAs to GBP/Wikipedia/socials) is how Google and AI engines confirm who you are. It feeds the knowledge panel and AI answer citations.",
               fix="Add MedicalOrganization JSON-LD with name, url, logo, telephone, address, areaServed, medicalSpecialty, sameAs[].",
               check_first="GSC: Enhancements/Rich results reports; search the brand name and see whether a knowledge panel appears.",
               confidence="high")]


def check_nap(site):
    addrs = Counter()
    for p in html_pages(site):
        for a in p.addresses:
            addrs[a] += 1
    if len(addrs) < 2:
        return []
    # group by street number + first word to find formatting variants of the same address
    groups = defaultdict(list)
    for a in addrs:
        groups[" ".join(re.sub(r"[^\w\s]", " ", a.lower()).split()[:2])].append(a)
    variants = {k: v for k, v in groups.items() if len(v) > 1}
    if not variants:
        return []
    ev = []
    for k, v in list(variants.items())[:4]:
        ev.append(" | ".join(f"'{a}' ({addrs[a]} pages)" for a in v[:3]))
    return [_f(id="nap_variants", category="local", title="Same address written in different ways across the site",
               severity=2, intent_weight=4, pages=[], page_count=sum(len(v) for v in variants.values()),
               evidence=ev, why_it_matters="NAP inconsistency between site, GBP and citations erodes local pack trust.",
               fix="Pick one canonical format per facility (match GBP exactly) and use it in footer, location pages and schema.",
               check_first="Compare against GBP listing and top citations (Psychology Today, SAMHSA locator).",
               confidence="low")]


# ----------------------------------------------------------------- trust
def check_trust(site):
    out = []
    pages = html_pages(site)
    idx = indexable(site)
    home = next((p for p in pages if p.page_type == "home"), None)
    accred_any = [p for p in pages if p.mentions.get("joint_commission") or p.mentions.get("carf")]
    if not accred_any:
        out.append(_f(id="no_accreditation", category="trust", title="No Joint Commission / CARF accreditation mentioned anywhere", severity=4, intent_weight=5,
                      pages=[home.final_url] if home else [], page_count=1,
                      evidence=[f"0 of {len(pages)} crawled pages mention Joint Commission, JCAHO or CARF"],
                      why_it_matters="Accreditation is the first trust check families (and AI answer engines) make; it is also a Google quality-rater signal for YMYL health pages.",
                      fix="If accredited, show the seal in the footer with a link to the accreditation page. If not, say what licensing applies.",
                      check_first="Confirm on qualitycheck.org / carf.org before claiming anything.", confidence="medium"))
    elif home and not (home.mentions.get("joint_commission") or home.mentions.get("carf")):
        out.append(_f(id="accreditation_not_on_home", category="trust", title="Accreditation mentioned on the site but not on the homepage", severity=2, intent_weight=5,
                      pages=[home.final_url], page_count=1,
                      evidence=[f"Mentioned on {len(accred_any)} pages, e.g. {accred_any[0].final_url}"],
                      why_it_matters="Most first visits land on the homepage; the seal belongs there and in the footer.",
                      fix="Add the seal and a one-line statement to the footer template.", check_first="None.", confidence="high"))
    if not any(p.mentions.get("legitscript") for p in pages):
        out.append(_f(id="no_legitscript", category="trust", title="No LegitScript certification mentioned", severity=2, intent_weight=4,
                      pages=[home.final_url] if home else [], page_count=1,
                      evidence=["No page mentions LegitScript"],
                      why_it_matters="LegitScript certification is required to run Google/Meta ads for addiction treatment and is a visible trust badge; its absence may also mean paid search is unavailable.",
                      fix="Get certified (if not) and show the badge in the footer.",
                      check_first="Check legitscript.com certified list for the facility.", confidence="medium"))
    ymyl = [p for p in idx if p.page_type in ("program", "content")]
    reviewed = [p for p in ymyl if p.mentions.get("medically_reviewed") or p.mentions.get("author_byline")]
    if ymyl and len(reviewed) < max(1, len(ymyl) * 0.2):
        out.append(_f(id="no_medical_review", category="trust", title="Program and blog pages lack medical reviewer / author bylines", severity=3, intent_weight=4,
                      pages=urls([p for p in ymyl if p not in reviewed]), page_count=len(ymyl) - len(reviewed),
                      evidence=[f"{len(reviewed)} of {len(ymyl)} program/content pages show 'medically reviewed' or a credentialed byline"],
                      why_it_matters="Health content without visible expertise ranks worse after Google's helpful-content/E-E-A-T updates and is less likely to be cited by AI engines.",
                      fix="Add 'Medically reviewed by <Name, credentials>' with a linked bio to every program and blog page.",
                      check_first="GSC: did blog/program clicks drop around core updates? Which pages lost positions 1-5?", confidence="medium"))
    staff = [p for p in idx if re.search(r"staff|team|leadership|clinical|our-people|providers", p.final_url + " " + p.title, re.I)]
    if not any(p.mentions.get("credentials") for p in staff):
        out.append(_f(id="no_staff_credentials", category="trust", title="No staff page with clinical credentials found", severity=2, intent_weight=3,
                      pages=urls(staff), page_count=len(staff),
                      evidence=[f"{len(staff)} staff/team pages crawled; none list MD/LCSW/LADAC-style credentials in text"],
                      why_it_matters="Named clinicians with credentials are what families, Google raters and AI engines use to judge legitimacy.",
                      fix="Clinical team page with photo, name, credentials, role; Person schema.",
                      check_first="None.", confidence="low"))
    return out


ALL_CHECKS = [check_robots_sitemap, check_links_and_redirects, check_indexability, check_titles_meta,
              check_thin_content, check_mobile_and_security, check_click_to_call, check_phone_consistency,
              check_admissions_path, check_location_pages, check_org_schema, check_nap, check_trust]
