"""Regression tests for bugs fixed in checks.py, ai_visibility.py and pagespeed.py (network-free)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seo_audit.models import Page  # noqa: E402
from seo_audit import checks, pagespeed  # noqa: E402
from seo_audit.ai_visibility import site_city_state, check_ai_visibility  # noqa: E402

BASE = "https://example-rehab.com"


def _p(path, page_type="program", weight=4, **kw):
    u = BASE + path
    kw.setdefault("status", 200)
    return Page(url=u, final_url=u, content_type="text/html", page_type=page_type, intent_weight=weight, **kw)


def _site(pages, **kw):
    s = {"pages": {p.url: p for p in pages}, "start_url": BASE + "/", "host": "example-rehab.com",
         "robots_status": 200, "robots_txt": "", "sitemap_sources": ["x"], "sitemap_errors": []}
    s.update(kw)
    return s


class RobotsSitemapTests(unittest.TestCase):
    def test_empty_pages_does_not_raise(self):
        self.assertEqual(checks.check_robots_sitemap(_site([])), [])

    def test_home_not_first_key(self):
        home = _p("/", "home", 5, error="blocked by robots.txt", status=0)
        site = _site([_p("/detox/"), home])
        self.assertIn("robots_blocks_home", [f.id for f in checks.check_robots_sitemap(site)])


class RedirectTests(unittest.TestCase):
    def test_start_url_redirect_is_not_a_chain(self):
        start = Page(url=BASE + "/", final_url="https://www.example-rehab.com/", status=200,
                     content_type="text/html", redirects=2, page_type="home", intent_weight=5)
        site = _site([start])
        self.assertEqual(checks.check_links_and_redirects(site), [])


class TitleTests(unittest.TestCase):
    def test_duplicate_titles_case_insensitive(self):
        site = _site([_p("/a/", title="Detox Program | Brand Name Here"),
                      _p("/b/", title="DETOX PROGRAM | Brand Name Here")])
        self.assertIn("titles_missing_dup", [f.id for f in checks.check_titles_meta(site)])


class AdmissionsPathTests(unittest.TestCase):
    def test_blog_post_about_insurance_is_not_insurance_page(self):
        site = _site([_p("/", "home", 5), _p("/blog/does-insurance-cover-rehab/", "content", 1)])
        self.assertIn("no_insurance_page", [f.id for f in checks.check_admissions_path(site)])


class NapTests(unittest.TestCase):
    def test_punctuation_variants_grouped(self):
        a = "123 Main, Suite 4 Nashville, TN 37201"
        b = "123 Main Suite 4, Nashville, TN 37201"
        site = _site([_p("/x/", addresses=[a]), _p("/y/", addresses=[b])])
        self.assertIn("nap_variants", [f.id for f in checks.check_nap(site)])


class CityStateTests(unittest.TestCase):
    def test_override_without_comma(self):
        self.assertEqual(site_city_state(_site([], city_override="Nashville")), ("Nashville", ""))

    def test_override_with_comma(self):
        self.assertEqual(site_city_state(_site([], city_override="Nashville, TN")), ("Nashville", "TN"))


class AiResultsTests(unittest.TestCase):
    def test_results_without_type_are_counted(self):
        site = _site([_p("/", "home", 5)], llms_txt_status=200, city_override="Nashville, TN")
        results = [{"query": "best alcohol rehab in Nashville, TN", "engine": "chatgpt", "cited": False},
                   {"query": "drug rehab in Nashville, TN", "engine": "chatgpt", "cited": False}]
        findings, _, _ = check_ai_visibility(site, brand="Acme", ai_results=results)
        self.assertIn("ai_answers_absent", [f.id for f in findings])


class PageSpeedTests(unittest.TestCase):
    def test_missing_lab_score_is_not_a_failure(self):
        site = _site([_p("/detox/")])
        r = {"url": BASE + "/detox/", "perf_score": None, "lab_lcp_s": 0, "lab_tbt_ms": 0, "field_lcp_ms": None,
             "field_inp_ms": None, "field_cls": None, "field_overall": None}
        self.assertEqual(pagespeed.check_pagespeed(site, [r]), [])

    def test_run_psi_null_score(self):
        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"lighthouseResult": {"categories": {"performance": {"score": None}}}}
        orig = pagespeed.requests.get
        pagespeed.requests.get = lambda *a, **k: R()
        try:
            self.assertIsNone(pagespeed.run_psi(BASE + "/")["perf_score"])
        finally:
            pagespeed.requests.get = orig

    def test_all_errors_no_finding(self):
        self.assertEqual(pagespeed.check_pagespeed(_site([]), [{"url": BASE, "error": "x"}]), [])


if __name__ == "__main__":
    unittest.main()
