"""Regression tests for market-data modules (openseo, backlinks, link_opportunities, topical_authority)."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seo_audit import backlinks, link_opportunities, openseo, topical_authority  # noqa: E402


def _write(out_dir, name, data):
    os.makedirs(os.path.join(out_dir, "openseo"), exist_ok=True)
    with open(os.path.join(out_dir, "openseo", f"{name}.json"), "w") as fh:
        json.dump(data, fh)


def _row(kw, url, etv=10, vol=100, rank=1):
    return {"keyword_data": {"keyword": kw, "keyword_info": {"search_volume": vol}},
            "ranked_serp_element": {"serp_item": {"url": url, "etv": etv, "rank_group": rank}}}


class MarketBugs(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    # ---------------------------------------------------------------- openseo
    def test_cached_error_stub_is_not_data_and_failures_do_not_overwrite_cache(self):
        _write(self.d, "x", {"error": "boom"})
        self.assertEqual(openseo._cached(self.d, "x", True, lambda: {"ok": 1}), {"ok": 1})
        def fail():
            raise RuntimeError("down")
        self.assertIn("error", openseo._cached(self.d, "x", False, fail))
        with open(os.path.join(self.d, "openseo", "x.json")) as fh:
            self.assertEqual(json.load(fh), {"ok": 1})

    def test_fetch_all_reuse_skips_geocode_when_maps_cached(self):
        for n in ("maps_alcohol_rehab", "maps_drug_rehab"):
            _write(self.d, n, {"results": []})
        with mock.patch.object(openseo, "geocode", side_effect=AssertionError("network")):
            data = openseo.fetch_all(None, "x.org", "X", "Nashville", "TN", self.d, reuse=True)
        self.assertEqual(set(data["maps"]), {"alcohol rehab", "drug rehab"})

    def test_kw_tolerates_null_subobjects(self):
        r = openseo._kw({"keyword_data": {"keyword": "a", "keyword_info": None}, "ranked_serp_element": None})
        self.assertEqual((r["keyword"], r["volume"], r["cpc"]), ("a", 0, 0))

    def test_strip_utm_keeps_meaningful_query(self):
        self.assertEqual(openseo._strip_utm("https://x.org/?page_id=5&utm_source=gbp#a"), "https://x.org/?page_id=5")

    def test_commercial_on_home_empty_city_does_not_match_everything(self):
        data = {"city": "", "state": "", "brand": "",
                "ranked_organic": {"keywords": [_row("best rehab for teens", "https://x.org/")]}}
        self.assertEqual(openseo.check_commercial_on_home({"pages": {}}, data), [])

    def test_local_pack_ignores_empty_or_error_maps(self):
        data = {"host": "x.org", "maps": {"alcohol rehab": {"error": "x"}, "drug rehab": {"results": []}}}
        self.assertEqual(openseo.check_local_pack({}, data), [])

    def test_market_summary_handles_null_competitor_metrics(self):
        data = {"host": "x.org", "competitors": {"competitors": [{"domain": "c.com", "visibility": None,
                                                                    "avg_position": None, "etv": None}]}}
        openseo.write_market_summary(data, self.d)
        self.assertTrue(os.path.exists(os.path.join(self.d, "market.md")))

    # ---------------------------------------------------------------- backlinks
    def _bl(self, rd, trends=None, refs=None):
        return {"overview": {"overview": {"summary": {"rank": 100, "referringDomains": rd, "backlinks": rd * 10},
                                          "trends": trends or []}},
                "referringDomains": {"rows": refs or []}}

    def test_backlinks_handles_null_trend_values_and_missing_ref_fields(self):
        trends = [{"date": "a", "backlinks": None, "referringDomains": 10}, {"date": "b", "backlinks": 5, "referringDomains": None}]
        _write(self.d, "backlinks_overview", self._bl(10, trends, refs=[{"spamScore": 50}, {"domain": "rehabdir.com"}]))
        _write(self.d, "backlinks_c.com", self._bl(50))
        with self.assertNoLogs("audit", level="WARNING"):
            out = backlinks.run({"start_url": "https://x.org/", "host": "x.org"},
                                {"competitors": [{"domain": "c.com"}, {"domain": "x.org"}]}, self.d)
        self.assertTrue(any(f.id == "bl_quality_mix" for f in out))
        self.assertTrue(all(f.page_count >= 0 for f in out))

    # ---------------------------------------------------------------- link_opportunities
    def test_link_gap_title_uses_market_city(self):
        mk = lambda dom: {"backlinks": {"rows": [{"domainFrom": dom, "domainFromRank": 50, "urlFrom": f"https://{dom}/"}]}}
        _write(self.d, "backlink_rows_x.org_p1", mk("own.org"))
        _write(self.d, "backlink_rows_recoveryranch.com_p1", mk("knoxnews.com"))
        out = link_opportunities.run({"start_url": "https://x.org/"}, {"city": "Knoxville"}, self.d)
        self.assertIn("Knoxville competitors", out[0].title)

    # ---------------------------------------------------------------- topical_authority
    def test_no_trailing_finding_when_site_leads_every_topic(self):
        _write(self.d, "ranked_keywords_organic", {"keywords": [_row("alcohol detox nashville", "https://x.org/a")]})
        _write(self.d, "ranked_c.com_traffic", {"keywords": [_row("random words", "https://c.com/", rank=50)]})
        out = topical_authority.run({"host": "x.org"}, {"topical_competitors": ["c.com"]}, self.d)
        self.assertFalse(any(f.id == "topical_authority_matrix" for f in out))


if __name__ == "__main__":
    unittest.main()
