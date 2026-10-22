#!/usr/bin/env python3
"""Render memo.md to memo.pdf with pandoc + headless Chrome. Usage: .venv/bin/python render_memo_pdf.py [memo.md] [memo.pdf]"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CHROME_CANDIDATES = (CHROME, "/Applications/Chromium.app/Contents/MacOS/Chromium",
                     "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                     "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome")


def find_chrome():
    """$CHROME, then the usual macOS app paths, then Chrome/Chromium on PATH. None if nothing is found."""
    for c in filter(None, (os.environ.get("CHROME"),) + CHROME_CANDIDATES):
        path = c if os.path.isabs(c) else shutil.which(c)
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None
CSS = """
@page { size: Letter; margin: 0.5in 0.55in; }
html, body { font-family: Helvetica, Arial, sans-serif; color: #111; }
body { font-size: 9.3pt; line-height: 1.3; margin: 0; }
h1 { font-size: 14pt; margin: 0 0 4pt 0; line-height: 1.2; }
h2 { font-size: 11pt; margin: 9pt 0 3pt 0; padding-top: 4pt; border-top: 0.6pt solid #888; }
h3 { font-size: 9.8pt; margin: 6pt 0 2pt 0; }
p { margin: 0 0 3pt 0; }
ul, ol { margin: 0 0 3pt 0; padding-left: 14pt; }
li { margin: 0 0 1pt 0; }
table { border-collapse: collapse; width: 100%; margin: 3pt 0 5pt 0; font-size: 8.6pt; page-break-inside: avoid; }
th, td { border: 0.5pt solid #bbb; padding: 2pt 4pt; vertical-align: top; text-align: left; }
th { background: #f0f0f0; }
code { font-family: Menlo, monospace; font-size: 8.4pt; }
h2, h3 { page-break-after: avoid; }
"""


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "memo.md"
    dst = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else "memo.pdf")
    if not shutil.which("pandoc"):
        sys.exit("render_memo_pdf: pandoc not found on PATH (brew install pandoc)")
    chrome = find_chrome()
    if not chrome:
        sys.exit("render_memo_pdf: Chrome/Chromium not found; install it or set CHROME=/path/to/chrome")
    body = subprocess.run(["pandoc", src, "-f", "gfm", "-t", "html5"], check=True, capture_output=True, text=True).stdout
    html = f"<!doctype html><html><head><meta charset='utf-8'><title>SEO memo</title><style>{CSS}</style></head><body>{body}</body></html>"
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as fh:
        fh.write(html)
        tmp = fh.name
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={dst}", Path(tmp).as_uri()],
                   check=True, capture_output=True)
    import re
    pages = len(re.findall(rb"/Type\s*/Page[^s]", open(dst, "rb").read()))
    print(f"{dst}: {pages} page(s)")


if __name__ == "__main__":
    main()
