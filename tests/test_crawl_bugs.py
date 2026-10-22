"""Regression tests for crawl/classify/models edge-case bugs."""
import gzip
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests  # noqa: E402

from seo_audit.classify import classify  # noqa: E402
from seo_audit.crawl import Crawler, is_asset, norm_host, normalize_url  # noqa: E402
from seo_audit.models import Page  # noqa: E402

BASE = "https://example-rehab.com"


def _resp(url, body, ctype="text/html", status=200):
    r = requests.Response()
    r.status_code = status
    r._content = body
    r.headers["Content-Type"] = ctype
    r.url = url
    r.encoding = requests.utils.get_encoding_from_headers(r.headers)
    return r


class NormalizeTests(unittest.TestCase):
    def test_uppercase_host_and_default_port(self):
        self.assertEqual(normalize_url("HTTPS://Example-Rehab.COM:443/Admissions/"), BASE + "/Admissions/")
        self.assertEqual(normalize_url("http://example-rehab.com:80/x"), "http://example-rehab.com/x")
        self.assertEqual(normalize_url("https://example-rehab.com:8443/x"), "https://example-rehab.com:8443/x")

    def test_norm_host_default_port(self):
        self.assertEqual(norm_host("www.example-rehab.com:443"), "example-rehab.com")

    def test_is_asset_modern_extensions(self):
        self.assertTrue(is_asset(BASE + "/img/hero.avif"))
        self.assertTrue(is_asset(BASE + "/files/brochure.pdf?v=2"))
        self.assertTrue(is_asset(BASE + "/media/tour.webm"))


class ExtractTests(unittest.TestCase):
    def test_link_with_explicit_port_is_internal(self):
        c = Crawler(BASE)
        page = Page(url=BASE + "/", final_url=BASE + "/")
        c.extract(page, '<html><body><a href="https://example-rehab.com:443/detox/">x</a></body></html>')
        self.assertEqual(page.internal_links, [BASE + "/detox/"])
        self.assertEqual(page.external_links, 0)

    def test_canonical_with_uppercase_host_matches_final_url(self):
        c = Crawler(BASE)
        page = Page(url=BASE + "/detox/", final_url=BASE + "/detox/")
        c.extract(page, '<html><head><link rel="canonical" href="https://EXAMPLE-REHAB.com/detox/"></head></html>')
        self.assertEqual(page.canonical, page.final_url)

    def test_utf8_page_without_charset_header(self):
        c = Crawler(BASE)
        c.robots.parse([])
        html = '<html><head><meta charset="utf-8"><title>Café Recovery – Nashville</title></head></html>'
        with mock.patch.object(c.session, "get", return_value=_resp(BASE + "/", html.encode("utf-8"))), \
                mock.patch("seo_audit.crawl.time.sleep"):
            page = c.fetch_page(BASE + "/")
        self.assertEqual(page.title, "Café Recovery – Nashville")


class SitemapTests(unittest.TestCase):
    def test_gzipped_sitemap(self):
        c = Crawler(BASE)
        c.robots_txt = "  Sitemap: " + BASE + "/sitemap.xml.gz\n"
        xml = ('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
               '<url><loc>' + BASE + '/admissions/</loc></url></urlset>').encode()
        r = _resp(BASE + "/sitemap.xml.gz", gzip.compress(xml), "application/x-gzip")
        with mock.patch.object(c.session, "get", return_value=r) as g:
            c.fetch_sitemaps()
        self.assertEqual(g.call_args[0][0], BASE + "/sitemap.xml.gz")
        self.assertEqual(c.sitemap_urls, [BASE + "/admissions/"])


class RunTests(unittest.TestCase):
    def test_redirect_target_not_crawled_twice(self):
        c = Crawler(BASE, max_pages=10, workers=1, delay=0)
        c.fetch_robots = lambda: c.robots.parse([])
        c.fetch_sitemaps = lambda: None
        fetched = []

        def fake_fetch(url):
            fetched.append(url)
            if url == BASE + "/":
                return Page(url=url, final_url=url, status=200, content_type="text/html",
                            internal_links=[BASE + "/detox"])
            # /detox 301s to /detox/, whose own markup links to itself
            return Page(url=url, final_url=BASE + "/detox/", status=200, content_type="text/html",
                        internal_links=[BASE + "/detox/"])

        c.fetch_page = fake_fetch
        out = c.run()
        self.assertEqual(fetched.count(BASE + "/detox/"), 0)
        self.assertEqual(len(out["pages"]), 2)
        self.assertEqual(out["home_final_url"], BASE + "/")


class ModelTests(unittest.TestCase):
    def test_content_type_case_insensitive(self):
        p = Page(url=BASE, status=200, content_type="Text/HTML; charset=UTF-8")
        self.assertTrue(p.indexable)
        self.assertTrue(Page(url=BASE, status=200, content_type="application/xhtml+xml").is_html)

    def test_robots_none_is_noindex(self):
        self.assertTrue(Page(url=BASE, meta_robots="none").noindex)
        self.assertTrue(Page(url=BASE, x_robots="googlebot: none").noindex)
        self.assertFalse(Page(url=BASE, meta_robots="index, follow").noindex)


class ClassifySubstringTests(unittest.TestCase):
    def test_program_pages_not_content(self):
        self.assertEqual(classify(BASE + "/depression-treatment/")[0], "program")
        self.assertEqual(classify(BASE + "/relapse-prevention-program/")[0], "program")
        self.assertEqual(classify(BASE + "/press-releases/")[0], "content")
        self.assertEqual(classify(BASE + "/events/")[0], "content")


if __name__ == "__main__":
    unittest.main()
