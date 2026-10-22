#!/usr/bin/env python3
"""Treatment-center SEO audit. Usage: python audit.py https://example.org [--max-pages 150] [--brand "Name"]"""
import argparse
import importlib
import json
import logging
import os
import pickle
import sys
import time
from urllib.parse import urlparse

from seo_audit.crawl import Crawler, norm_host


def load_dotenv(path=".env"):
    """Read KEY=VALUE lines from .env next to this script. Real environment variables win."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    if not os.path.exists(path):
        return
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def doctor():
    """Print what is configured and what will run."""
    import requests
    print(f"python {sys.version.split()[0]}")
    url, pid = os.environ.get("OPENSEO_MCP_URL", ""), os.environ.get("OPENSEO_PROJECT_ID", "")
    if url and pid:
        try:
            r = requests.post(url, json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                         "params": {"name": "list_projects", "arguments": {}}},
                              headers={"Accept": "application/json, text/event-stream"}, timeout=15)
            names = [p["id"] for p in r.json()["result"]["structuredContent"]["projects"]]
            print(f"OpenSEO      OK  {url}  project {'found' if pid in names else 'NOT found: ' + pid}")
        except Exception as e:
            print(f"OpenSEO      unreachable ({e.__class__.__name__}) at {url}. Market-data checks will be skipped unless --reuse finds cached data.")
    else:
        print("OpenSEO      not configured (OPENSEO_MCP_URL / OPENSEO_PROJECT_ID). Crawler checks only, or --reuse on cached data.")
    print(f"PageSpeed    {'key set' if os.environ.get('PSI_API_KEY') else 'no key: a few free calls per day, then 429. Use --no-psi or set PSI_API_KEY'}")
    print(f"Perplexity   {'key set: script runs the AI queries' if os.environ.get('PERPLEXITY_API_KEY') else 'no key: run the AI queries by hand and pass --ai-results file.json'}")
    cached = [d for d in (os.listdir("out") if os.path.isdir("out") else []) if os.path.exists(os.path.join("out", d, "crawl.pkl"))]
    print(f"Cached runs  {', '.join(cached) if cached else 'none'}  (re-score with --reuse, no keys or credits needed)")
from seo_audit.checks import ALL_CHECKS
from seo_audit.ai_visibility import check_ai_visibility
from seo_audit.pagespeed import run_all as run_psi, check_pagespeed
from seo_audit.report import rank, write_outputs

# Deeper analyses. Each module exposes run(site, market, out_dir, client) -> list[Finding],
# writes its own markdown file into out_dir and handles its own caching for --reuse.
DEEP_MODULES = ("backlinks", "link_opportunities", "onpage", "competitor_pages", "topical_authority", "geo_mentions")
SKIPPABLE = DEEP_MODULES + ("openseo", "psi")


def run_deep_modules(site, market, out_dir, client, skip):
    """Import and run each deeper-analysis module. A missing or failing module is logged and skipped."""
    findings = []
    for name in DEEP_MODULES:
        if name in skip:
            logging.info("skipping %s (--skip)", name)
            continue
        try:
            mod = importlib.import_module(f"seo_audit.{name}")
        except ImportError as e:
            logging.warning("module %s not available (%s)", name, e)
            continue
        except Exception as e:  # a half-written module must not stop the audit
            logging.exception("module %s failed to import: %s", name, e)
            continue
        try:
            logging.info("running %s", name)
            findings.extend(mod.run(site, market, out_dir, client) or [])
        except Exception as e:
            logging.exception("module %s failed: %s", name, e)
    return findings


def main():
    ap = argparse.ArgumentParser(description="Audit a treatment-center website for the SEO problems that cost calls and admissions.")
    ap.add_argument("url", nargs="?", help="Start URL, e.g. https://www.example.org")
    ap.add_argument("--doctor", action="store_true", help="Show what is configured (keys, OpenSEO reachability, cached runs) and exit")
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
    ap.add_argument("--skip", default="", help="Comma list of pieces to skip: " + ",".join(SKIPPABLE))
    args = ap.parse_args()
    skip = {s.strip() for s in args.skip.split(",") if s.strip()}
    unknown = skip - set(SKIPPABLE)
    if unknown:
        ap.error(f"--skip: unknown name(s) {', '.join(sorted(unknown))}; choose from {','.join(SKIPPABLE)}")
    if "openseo" in skip:
        args.no_openseo = True
    if "psi" in skip:
        args.no_psi = True
    load_dotenv()
    if args.doctor:
        return doctor()
    if not args.url:
        ap.error("a start URL is required (or use --doctor)")
    args.openseo_url = args.openseo_url or os.environ.get("OPENSEO_MCP_URL", "")
    args.openseo_project = args.openseo_project or os.environ.get("OPENSEO_PROJECT_ID", "")

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

    market, client = None, None  # stay None when the market-data block is skipped
    have_endpoint = bool(args.openseo_url and args.openseo_project)
    have_cache = args.reuse and os.path.isdir(os.path.join(out_dir, "openseo"))
    if (have_endpoint or have_cache) and not args.no_openseo:
        from seo_audit.openseo import OpenSEO, fetch_all, ALL_OPENSEO_CHECKS, write_market_summary
        from seo_audit.ai_visibility import site_city_state
        city, state = site_city_state(site)
        logging.info("OpenSEO market data for %s (%s, %s)%s", site["host"], city, state, " [cached]" if args.reuse else "")
        client = OpenSEO(args.openseo_url, args.openseo_project) if have_endpoint else None
        market = fetch_all(client, site["host"], brand, city, state, out_dir, reuse=args.reuse)
        for check in ALL_OPENSEO_CHECKS:
            try:
                findings.extend(check(site, market))
            except Exception as e:
                logging.exception("openseo check %s failed: %s", check.__name__, e)
        write_market_summary(market, out_dir)
    elif not args.no_openseo:
        logging.warning("OpenSEO not configured: skipping market-data checks (set OPENSEO_MCP_URL and OPENSEO_PROJECT_ID in .env, or use --reuse on a cached run)")

    findings.extend(run_deep_modules(site, market or None, out_dir, client, skip))

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
