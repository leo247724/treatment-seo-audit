#!/usr/bin/env python3
"""Treatment-center SEO audit. Usage: python audit.py https://example.org [--max-pages 150] [--brand "Name"]"""
import argparse
import json
import logging
import os
import pickle
import sys
import time
from urllib.parse import urlparse

from seo_audit.crawl import Crawler, norm_host
from seo_audit.checks import ALL_CHECKS
from seo_audit.ai_visibility import check_ai_visibility
from seo_audit.pagespeed import run_all as run_psi, check_pagespeed
from seo_audit.report import rank, write_outputs


def main():
    ap = argparse.ArgumentParser(description="Audit a treatment-center website for the SEO problems that cost calls and admissions.")
    ap.add_argument("url", help="Start URL, e.g. https://www.example.org")
    ap.add_argument("--max-pages", type=int, default=150)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default="out", help="Output root; results go to <out>/<host>/")
    ap.add_argument("--brand", default="", help="Brand name for AI answer queries (default: first part of the homepage title)")
    ap.add_argument("--no-psi", action="store_true", help="Skip PageSpeed Insights calls (slow, ~30-60s per page)")
    ap.add_argument("--psi-pages", type=int, default=4)
    ap.add_argument("--ai-results", help="JSON file of manually checked AI answers (see README)")
    ap.add_argument("--reuse", action="store_true", help="Reuse cached crawl, PageSpeed and OpenSEO data from the last run (fast re-score, no credits)")
    ap.add_argument("--city", default="", help='Facility city for market queries, e.g. "Nashville, TN" (default: detected from addresses)')
    ap.add_argument("--openseo-url", default=os.environ.get("OPENSEO_MCP_URL", ""), help="OpenSEO MCP endpoint (or env OPENSEO_MCP_URL)")
    ap.add_argument("--openseo-project", default=os.environ.get("OPENSEO_PROJECT_ID", ""), help="OpenSEO project id (or env OPENSEO_PROJECT_ID)")
    ap.add_argument("--no-openseo", action="store_true", help="Skip the OpenSEO market-data pulls")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    t0 = time.time()
    url = args.url if args.url.startswith("http") else "https://" + args.url
    out_dir = os.path.join(args.out, norm_host(urlparse(url).netloc))
    os.makedirs(out_dir, exist_ok=True)
    cache = os.path.join(out_dir, "crawl.pkl")
    psi_cache = os.path.join(out_dir, "psi.json")

    if args.reuse and os.path.exists(cache):
        logging.info("reusing cached crawl %s", cache)
        with open(cache, "rb") as fh:
            site = pickle.load(fh)
    else:
        site = Crawler(url, max_pages=args.max_pages, workers=args.workers).run()
        with open(cache, "wb") as fh:
            pickle.dump(site, fh)

    site["city_override"] = args.city
    home = site["pages"].get(next(iter(site["pages"])))
    brand = args.brand or (home.title.split("|")[0].split("-")[0].split(":")[0].strip() if home and home.title else site["host"])
    logging.info("brand assumed: %r (override with --brand)", brand)

    findings = []
    for check in ALL_CHECKS:
        try:
            findings.extend(check(site))
        except Exception as e:  # a failing check must not hide the others
            logging.exception("check %s failed: %s", check.__name__, e)

    ai_results = None
    if args.ai_results:
        with open(args.ai_results) as fh:
            ai_results = json.load(fh)
    ai_findings, access, ai_results = check_ai_visibility(site, brand=brand, ai_results=ai_results, out_dir=out_dir)
    findings.extend(ai_findings)

    if args.openseo_url and args.openseo_project and not args.no_openseo:
        from seo_audit.openseo import OpenSEO, fetch_all, ALL_OPENSEO_CHECKS, write_market_summary
        from seo_audit.ai_visibility import site_city_state
        city, state = site_city_state(site)
        logging.info("OpenSEO market data for %s (%s, %s)%s", site["host"], city, state, " [cached]" if args.reuse else "")
        market = fetch_all(OpenSEO(args.openseo_url, args.openseo_project), site["host"], brand, city, state, out_dir, reuse=args.reuse)
        for check in ALL_OPENSEO_CHECKS:
            try:
                findings.extend(check(site, market))
            except Exception as e:
                logging.exception("openseo check %s failed: %s", check.__name__, e)
        write_market_summary(market, out_dir)

    psi_results = []
    if not args.no_psi:
        if args.reuse and os.path.exists(psi_cache):
            with open(psi_cache) as fh:
                psi_results = json.load(fh)
        else:
            psi_results = run_psi(site, key=os.environ.get("PSI_API_KEY"), n=args.psi_pages)
            with open(psi_cache, "w") as fh:
                json.dump(psi_results, fh, indent=2)
        findings.extend(check_pagespeed(site, psi_results))

    findings = rank(findings)
    path = write_outputs(site, findings, psi_results, ai_results, access, out_dir, brand=brand)
    logging.info("done in %.0fs -> %s", time.time() - t0, path)
    print(f"\nTop findings for {site['host']}:")
    for i, f in enumerate(findings[:8], 1):
        print(f"{i:>2}. [{f.impact:>5}] sev {f.severity} intent {f.intent_weight} pages {f.page_count:<4} {f.title}")
    print(f"\nFull report: {path}")


if __name__ == "__main__":
    sys.exit(main())
