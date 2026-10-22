"""Regression tests for onpage / competitor_pages / geo_mentions bugs (network-free)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seo_audit import onpage, competitor_pages as cp, geo_mentions as gm  # noqa: E402
from seo_audit.models import Page  # noqa: E402

BASE = "https://example-rehab.com"


def _page(path, **kw):
    kw.setdefault("status", 200)
    kw.setdefault("content_type", "text/html")
    kw.setdefault("intent_weight", 4)
    return Page(url=BASE + path, final_url=BASE + path, **kw)


class OnpageTests(unittest.TestCase):
    def test_location_pages_under_resources_not_skipped(self):
        site = {"pages": {p.url: p for p in [_page("/resources/location/nashville-music-row/"),
                                             _page("/resources/blog/what-to-expect/")]}}
        urls = [p.url for p in onpage.select_pages(site)]
        self.assertEqual(urls, [BASE + "/resources/location/nashville-music-row/"])

    def test_suggest_title_no_brand_duplicate(self):
        t = onpage.suggest_title(_page("/x/", title="Cumberland Heights | Rehab", page_type="program"))
        self.assertEqual(t.count("Cumberland Heights"), 1, t)
        self.assertLessEqual(len(t), 60)

    def test_suggest_title_long_slug_capped_at_60(self):
        p = _page("/treatment/dual-diagnosis-and-co-occurring-disorders-treatment/", title="", page_type="program")
        self.assertLessEqual(len(onpage.suggest_title(p)), 60)


class CompetitorPagesTests(unittest.TestCase):
    def test_competitor_urls_dedupe_www_and_slash(self):
        market = {"serps": {"results": [{"items": [
            {"type": "organic", "url": "https://www.a.com/rehab/"},
            {"type": "organic", "url": "https://a.com/rehab"},
            {"type": "local_pack", "domain": "b.com"}]}]}}
        self.assertEqual(cp._competitor_urls(market), ["https://www.a.com/rehab/", "https://b.com"])

    def test_header_tel_role_banner(self):
        html = '<html><body><div role="banner"><a href="tel:6155551212">Call</a></div><main>x</main></body></html>'
        self.assertTrue(cp.extract(BASE + "/", html, "competitor")["header_tel"])

    def test_24_hours_of_therapy_not_24_7(self):
        html = "<html><body><main><p>Clients get 24 hours of therapy each week.</p></main></body></html>"
        row = cp.extract(BASE + "/", html, "competitor")
        self.assertFalse(row["mentions_24_7"])
        self.assertFalse(row["strategy"]["mentions_24_7"])
        html2 = "<html><body><main><p>Admissions open 24 hours a day.</p></main></body></html>"
        self.assertTrue(cp.extract(BASE + "/", html2, "competitor")["mentions_24_7"])

    def test_insurer_logos_counted_once_per_insurer(self):
        html = "<html><body>" + '<img alt="Aetna logo">' * 3 + '<img alt="Cigna">' + "</body></html>"
        self.assertEqual(cp.analyze(BASE + "/", html)["strategy"]["insurer_logos"], 2)

    def test_atomic_write_cleans_tmp_on_failure(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.json")
            os.makedirs(path)  # os.replace onto a directory fails
            with self.assertRaises(OSError):
                cp._atomic_write(path, "data")
            self.assertFalse(os.path.exists(path + ".tmp"))


class GeoMentionsTests(unittest.TestCase):
    def test_table_never_raises_on_bad_input(self):
        self.assertEqual(gm.share_of_voice_table(None), "")

    def test_table_host_none_with_brand_mentions_list(self):
        data = {"brands": [{"name": "A", "domains": ["a.com"]}],
                "queries": [{"type": "non-brand", "query": "q", "citations": [],
                             "brand_mentions": [{"brand": "A", "mentioned_in_answer": True,
                                                 "position_of_first_mention": None}, {"cited": True}]}]}
        t = gm.share_of_voice_table(data, None)
        self.assertIn("| A | 1/1 (100%) | 0/1 (0%) | - |", t)


if __name__ == "__main__":
    unittest.main()
