"""Regression tests for entry-point / glue bugs (audit.py, report.py, run_sites.sh, setup.sh)."""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import audit  # noqa: E402
from seo_audit import report  # noqa: E402
from seo_audit.ai_visibility import site_city_state  # noqa: E402


class DotenvTests(unittest.TestCase):
    def test_export_equals_and_quotes(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, ".env")
            with open(p, "w") as fh:
                fh.write("export T_A=1\nT_B=a=b==\nT_C=\"it's\"\nT_D='x\"'\n")
            with mock.patch.dict(os.environ, {}, clear=False):
                for k in ("T_A", "T_B", "T_C", "T_D"):
                    os.environ.pop(k, None)
                audit.load_dotenv(p)
                self.assertEqual(os.environ["T_A"], "1")
                self.assertEqual(os.environ["T_B"], "a=b==")
                self.assertEqual(os.environ["T_C"], "it's")
                self.assertEqual(os.environ["T_D"], 'x"')


class GlueTests(unittest.TestCase):
    def test_out_dir_strips_port_and_case(self):
        self.assertEqual(audit.site_dir_name("https://WWW.Example.ORG:8443/path"), "example.org")

    def test_city_without_comma_is_city_not_state(self):
        site = {"city_override": audit.normalize_city("Nashville"), "pages": {}}
        self.assertEqual(site_city_state(site), ("Nashville", ""))
        self.assertEqual(audit.normalize_city("Nashville, TN"), "Nashville, TN")
        self.assertEqual(audit.normalize_city(""), "")

    def test_old_pickle_gets_missing_keys(self):
        site = audit.upgrade_cached_site({"host": "x.org", "start_url": "https://x.org/", "pages": {}})
        self.assertEqual(site["llms_txt_status"], 0)
        self.assertEqual(site["sitemap_urls"], [])

    def _site(self, title, host="cumberlandheights.org"):
        home = types.SimpleNamespace(title=title)
        other = types.SimpleNamespace(title="Blog post | Something")
        return {"host": host, "start_url": "https://cumberlandheights.org/",
                "home_final_url": "https://cumberlandheights.org/",
                "pages": {"https://cumberlandheights.org/blog/": other, "https://cumberlandheights.org/": home}}

    def test_brand_from_home_page_not_first_crawled(self):
        self.assertEqual(audit.derive_brand(self._site("Cumberland Heights | Rehab")), "Cumberland Heights")

    def test_brand_after_separator(self):
        self.assertEqual(audit.derive_brand(self._site("Addiction Treatment in Nashville | Cumberland Heights")),
                         "Cumberland Heights")

    def test_brand_empty_title_falls_back_to_host(self):
        self.assertEqual(audit.derive_brand(self._site("   ")), "cumberlandheights.org")

    def test_brand_keeps_hyphenated_name(self):
        self.assertEqual(audit.derive_brand(self._site("Al-Anon Family Groups", host="al-anon.org")), "Al-Anon Family Groups")

    def test_doctor_ignores_files_in_out_root(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "notes.txt"), "w").close()
            os.makedirs(os.path.join(d, "a.org"))
            open(os.path.join(d, "a.org", "crawl.pkl"), "w").close()
            buf = io.StringIO()
            with mock.patch.dict(os.environ, {"OPENSEO_MCP_URL": "", "OPENSEO_PROJECT_ID": ""}), \
                    contextlib.redirect_stdout(buf):
                audit.doctor(d)
            self.assertIn("Cached runs  a.org", buf.getvalue())


class ReportTests(unittest.TestCase):
    def test_passes_no_false_claims_on_empty_crawl(self):
        site = {"pages": {}, "sitemap_sources": ["https://x.org/sitemap.xml"], "sitemap_urls": []}
        out = report.passes(site, [], {})
        self.assertFalse(any("tel:" in p for p in out))
        self.assertFalse(any("XML sitemap found" in p for p in out))

    def test_table_cell_escapes_pipes_and_newlines(self):
        self.assertEqual(report.cell("a | b\nc"), "a \\| b c")


class ShellTests(unittest.TestCase):
    def test_bash_syntax(self):
        for f in ("schedule/run_sites.sh", "setup.sh"):
            subprocess.run(["bash", "-n", os.path.join(ROOT, f)], check=True)

    def test_run_sites_via_symlink_in_pipe_space_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, "elev8 | REPO ", "r")
            os.makedirs(os.path.join(repo, "schedule"))
            shutil.copy(os.path.join(ROOT, "schedule", "run_sites.sh"), os.path.join(repo, "schedule"))
            shutil.copy(os.path.join(ROOT, "diff_runs.py"), repo)
            with open(os.path.join(repo, "schedule", "sites.txt"), "w") as fh:
                fh.write("https://www.Example.org | Example Brand | Nashville, TN\n")
            fake = os.path.join(repo, "fakepy")
            with open(fake, "w") as fh:
                fh.write('#!/usr/bin/env bash\nif [ "$1" = audit.py ]; then\n'
                         '  printf "%s\\n" "$@" > args.txt; mkdir -p out/example.org; echo "[]" > out/example.org/findings.json\n'
                         f'else exec "{sys.executable}" "$@"; fi\n')
            os.chmod(fake, 0o755)
            link_dir = os.path.join(tmp, "bin")
            os.makedirs(link_dir)
            link = os.path.join(link_dir, "run_sites.sh")
            os.symlink(os.path.join(repo, "schedule", "run_sites.sh"), link)
            subprocess.run(["bash", link], cwd=tmp, env={**os.environ, "PYTHON": fake}, check=True,
                           capture_output=True)
            with open(os.path.join(repo, "args.txt")) as fh:
                args = fh.read().splitlines()
            self.assertIn("Example Brand", args)
            self.assertIn("Nashville, TN", args)
            self.assertIn("--no-psi", args)
            self.assertFalse(os.path.exists(os.path.join(repo, "schedule", "logs", ".run_sites.lock")))
            hist = os.path.join(repo, "out", "example.org", "history")
            self.assertEqual(len(os.listdir(hist)), 1)


if __name__ == "__main__":
    unittest.main()
