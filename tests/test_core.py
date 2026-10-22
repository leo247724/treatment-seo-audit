"""Focused unit tests for the core, network-free parts of seo_audit."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seo_audit.classify import classify, WEIGHTS  # noqa: E402
from seo_audit.crawl import normalize_url, is_asset, PHONE_RE, ADDR_RE, Crawler  # noqa: E402
from seo_audit.models import Finding, Page  # noqa: E402
from seo_audit.report import rank  # noqa: E402
from seo_audit.ai_visibility import bot_access, AI_BOTS  # noqa: E402
from seo_audit.checks import check_click_to_call  # noqa: E402

BASE = "https://example-rehab.com"


class ClassifyTests(unittest.TestCase):
    def test_home(self):
        for u in (BASE + "/", BASE, BASE + "/index.html"):
            self.assertEqual(classify(u), ("home", 5), u)

    def test_conversion(self):
        self.assertEqual(classify(BASE + "/insurance/"), ("conversion", 5))
        self.assertEqual(classify(BASE + "/admissions/"), ("conversion", 5))

    def test_local(self):
        self.assertEqual(classify(BASE + "/locations/nashville/"), ("local", 4))

    def test_program(self):
        self.assertEqual(classify(BASE + "/alcohol-rehab/"), ("program", 4))

    def test_content(self):
        self.assertEqual(classify(BASE + "/blog/what-is-detox/"), ("content", 1))

    def test_archive(self):
        for u in ("/tag/insurance/", "/category/news/", "/member-category/rehab/",
                  "/page/2/", "/blog/page/3/"):
            self.assertEqual(classify(BASE + u), ("archive", 1), u)
        self.assertEqual(WEIGHTS["archive"], 1)

    def test_title_is_used(self):
        self.assertEqual(classify(BASE + "/xyz/", "Verify Your Insurance"), ("conversion", 5))

    def test_image_named_insurance_is_asset(self):
        for u in (BASE + "/insurance-card.png",
                  BASE + "/wp-content/uploads/2024/01/insurance-logo.jpg"):
            self.assertTrue(is_asset(u), u)


class CrawlHelperTests(unittest.TestCase):
    def test_normalize_keeps_trailing_slash(self):
        self.assertEqual(normalize_url(BASE + "/admissions/"), BASE + "/admissions/")
        self.assertEqual(normalize_url(BASE + "/admissions"), BASE + "/admissions")

    def test_normalize_drops_query_and_fragment(self):
        self.assertEqual(normalize_url(BASE + "/insurance/?utm_source=x#verify"), BASE + "/insurance/")

    def test_normalize_empty_path(self):
        self.assertEqual(normalize_url(BASE), BASE + "/")

    def test_is_asset(self):
        self.assertTrue(is_asset(BASE + "/files/brochure.PDF"))
        self.assertTrue(is_asset(BASE + "/wp-content/themes/x/style"))
        self.assertTrue(is_asset(BASE + "/wp-includes/js/jquery"))
        self.assertFalse(is_asset(BASE + "/insurance/"))
        self.assertFalse(is_asset(BASE + "/"))

    def test_phone_re(self):
        text = "Call 615-356-2700 or toll free (800) 646-9998 today."
        self.assertEqual(["".join(m) for m in PHONE_RE.findall(text)], ["6153562700", "8006469998"])

    def test_addr_re(self):
        m = ADDR_RE.search("Visit us at 8283 River Road Pike, Nashville, TN 37209 for a tour.")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(0), "8283 River Road Pike, Nashville, TN 37209")

    def test_jsonld_types_flatten_graph(self):
        data = {"@graph": [{"@type": "Organization"}, {"@type": ["WebPage", "FAQPage"]}]}
        self.assertEqual(Crawler._types(data), ["Organization", "WebPage", "FAQPage"])


def _finding(fid, severity, intent, count):
    return Finding(id=fid, category="conversion", title=fid, severity=severity, intent_weight=intent,
                   pages=[], page_count=count, evidence=[], why_it_matters="", fix="", check_first="")


class ScoringTests(unittest.TestCase):
    def test_score_formula(self):
        self.assertEqual(_finding("a", 5, 5, 1).score(), 25.0)
        self.assertEqual(_finding("b", 3, 4, 100).score(), 24.0)  # reach capped at 2
        self.assertEqual(_finding("c", 2, 2, 0).score(), 4.0)     # page_count floor of 1

    def test_severe_high_intent_beats_broad_lower_severity(self):
        a, b = _finding("a", 5, 5, 1), _finding("b", 3, 4, 100)
        self.assertGreater(a.score(), b.score())

    def test_rank_sorts_descending(self):
        fs = [_finding("low", 1, 1, 1), _finding("broad", 3, 4, 100), _finding("top", 5, 5, 1),
              _finding("mid", 4, 4, 10)]
        ranked = rank(fs)
        self.assertEqual([f.id for f in ranked], ["mid", "top", "broad", "low"])
        impacts = [f.impact for f in ranked]
        self.assertEqual(impacts, sorted(impacts, reverse=True))


class BotAccessTests(unittest.TestCase):
    def _site(self, robots):
        return {"robots_txt": robots, "home_final_url": BASE + "/", "start_url": BASE + "/"}

    def test_disallowed_bot_is_false_others_true(self):
        robots = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
        access = bot_access(self._site(robots))
        self.assertEqual(set(access), set(AI_BOTS))
        self.assertFalse(access["GPTBot"])
        self.assertTrue(access["OAI-SearchBot"])
        self.assertTrue(access["Googlebot"])

    def test_empty_robots_allows_all(self):
        access = bot_access(self._site(""))
        self.assertTrue(all(access.values()))


def _page(path, tel, page_type="program", weight=4):
    u = BASE + path
    return Page(url=u, final_url=u, status=200, content_type="text/html; charset=utf-8",
                page_type=page_type, intent_weight=weight,
                tel_links=["tel:+16153562700"] if tel else [], header_has_tel=tel)


class ClickToCallTests(unittest.TestCase):
    def test_finding_when_high_intent_page_lacks_tel(self):
        pages = [_page("/", True, "home", 5), _page("/detox/", False)]
        site = {"pages": {p.url: p for p in pages}}
        out = check_click_to_call(site)
        ids = [f.id for f in out]
        self.assertIn("no_tel_link", ids)
        f = next(f for f in out if f.id == "no_tel_link")
        self.assertEqual(f.severity, 5)
        self.assertEqual(f.page_count, 1)
        self.assertIn(BASE + "/detox/", f.pages)

    def test_no_finding_when_all_pages_have_tel(self):
        pages = [_page("/", True, "home", 5), _page("/detox/", True), _page("/insurance/", True, "conversion", 5)]
        site = {"pages": {p.url: p for p in pages}}
        self.assertEqual(check_click_to_call(site), [])


if __name__ == "__main__":
    unittest.main()
