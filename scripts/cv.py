#!/usr/bin/env python3
"""Build the CV PDF and keep its side-project progress line up to date.

Usage (from the repository root, on macOS, Linux or Windows):

    python scripts/cv.py build    Print index.html to the PDF and check it is one page.
    python scripts/cv.py sync     Copy open-conqueror's progress summary into index.html.

Only the Python standard library is used, so there is nothing to install
besides Python 3.9+ and a Chromium-based browser (Chrome, Edge, Brave, Chromium).
"""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML_FILE = ROOT / "index.html"
PDF_FILE = ROOT / "Pablo-Torres-CV.pdf"

# The progress summary lives in the project it describes, so it is updated
# together with the work. It is one line of plain text.
SUMMARY_URL = (
    "https://raw.githubusercontent.com/pablot30/open-conqueror/main/docs/cv-summary.txt"
)
# Two printed lines in the side-project bullet. Longer text could push the CV
# onto a second page, which the build step would then refuse.
SUMMARY_MAX_CHARS = 260

MARKERS = re.compile(r"(<!-- so-far:start -->)(.*?)(<!-- so-far:end -->)", re.DOTALL)

BROWSER_CANDIDATES = {
    "darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ],
    "win32": [
        r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
        r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
        r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
        r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
    ],
}
BROWSER_COMMANDS = [
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
    "brave-browser",
]


def find_browser() -> str:
    """Return the path of a Chromium-based browser, or exit with a clear message."""
    override = os.environ.get("CV_BROWSER")
    if override:
        return override
    for candidate in BROWSER_CANDIDATES.get(sys.platform, []):
        path = Path(os.path.expandvars(candidate))
        if path.is_file():
            return str(path)
    for command in BROWSER_COMMANDS:
        found = shutil.which(command)
        if found:
            return found
    sys.exit(
        "No Chromium-based browser found. Install Chrome, Edge, Brave or Chromium, "
        "or set CV_BROWSER to the browser's path."
    )


def count_pages(pdf: Path) -> int:
    """Count pages in a PDF written by Chrome (uncompressed page objects)."""
    data = pdf.read_bytes()
    return len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", data))


def build() -> None:
    browser = find_browser()
    with tempfile.TemporaryDirectory() as profile:
        result = subprocess.run(
            [
                browser,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                f"--user-data-dir={profile}",
                "--no-pdf-header-footer",
                f"--print-to-pdf={PDF_FILE}",
                HTML_FILE.as_uri(),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    if result.returncode != 0 or not PDF_FILE.is_file():
        sys.exit(f"The browser could not print the PDF:\n{result.stderr}")
    pages = count_pages(PDF_FILE)
    if pages != 1:
        sys.exit(f"{PDF_FILE.name} has {pages} pages. Shorten the text until it fits on one.")
    print(f"Built {PDF_FILE.name}: 1 page.")


def sync(source: str) -> None:
    if source.startswith(("http://", "https://")):
        try:
            with urllib.request.urlopen(source, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            if error.code == 404:
                print(f"No summary published yet at {source}. index.html is unchanged.")
                return
            raise
    else:
        raw = Path(source).read_text(encoding="utf-8")

    summary = " ".join(raw.split())
    if not summary:
        sys.exit("The summary is empty. index.html is unchanged.")
    if len(summary) > SUMMARY_MAX_CHARS:
        sys.exit(
            f"The summary has {len(summary)} characters; the CV has room for "
            f"{SUMMARY_MAX_CHARS}. Shorten it in open-conqueror."
        )

    page = HTML_FILE.read_text(encoding="utf-8")
    if not MARKERS.search(page):
        sys.exit("index.html has no so-far markers. Add them around the progress text.")
    escaped = html.escape(summary, quote=False)
    updated = MARKERS.sub(lambda m: f"{m.group(1)}{escaped}{m.group(3)}", page, count=1)
    if updated == page:
        print("The progress summary is already current.")
        return
    HTML_FILE.write_text(updated, encoding="utf-8", newline="\n")
    print("Updated the progress summary in index.html.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="print index.html to the PDF and check it is one page")
    sync_parser = sub.add_parser("sync", help="copy open-conqueror's progress summary into index.html")
    sync_parser.add_argument(
        "--source",
        default=SUMMARY_URL,
        help="URL or local file with the summary (default: open-conqueror on GitHub)",
    )
    args = parser.parse_args()
    if args.command == "build":
        build()
    else:
        sync(args.source)


if __name__ == "__main__":
    main()
