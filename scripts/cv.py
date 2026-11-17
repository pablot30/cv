#!/usr/bin/env python3
"""Build the CV PDF, check it against STYLE.md, and sync text from open-conqueror.

Usage (from the repository root, on macOS, Linux or Windows):

    python scripts/cv.py build    Print index.html to the PDF and run every check.
    python scripts/cv.py check    Run the checks without writing the PDF.
    python scripts/cv.py sync     Copy open-conqueror's CV text into index.html.

Only the Python standard library is used, so there is nothing to install
besides Python 3.9+ and a Chromium-based browser (Chrome, Edge, Brave, Chromium).
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML_FILE = ROOT / "index.html"
PDF_FILE = ROOT / "Pablo-Torres-CV.pdf"

SOURCE_BASE = "https://raw.githubusercontent.com/pablot30/open-conqueror/main/"


@dataclass(frozen=True)
class Field:
    """A piece of the CV that is filled in from a file in open-conqueror."""

    marker: str  # name of the <!-- name:start --> ... <!-- name:end --> markers
    source: str  # path of the plain-text file in open-conqueror
    max_chars: int  # a quick first limit; the real limit is data-max-lines
    sentence: bool  # True: must end with a full stop. False: must not.


FIELDS = (
    Field("so-far", "docs/cv-summary.txt", 240, sentence=True),
    Field("ai-tools", "docs/cv-ai-tools.txt", 100, sentence=False),
)

# STYLE.md: no specific microcontroller boards.
BANNED_WORDS = ("Arduino", "ESP32", "UNO")
# STYLE.md: black and white only. Any other CSS color fails the check.
ALLOWED_COLORS = {"#000", "#000000", "#fff", "#ffffff"}
# STYLE.md: no widows. A last line narrower than this share of its block fails.
MIN_LAST_LINE = 0.12

# A4 at 96 dpi. index.html lays out the screen sheet exactly like the printed
# page at this width, so lines break in the same places in both.
A4_WINDOW = "794,1123"

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

# Measures the rendered page and reports layout problems. It is injected into
# a temporary copy of index.html only; the published page has no script.
LAYOUT_PROBE = """
<script>
(() => {
  const problems = [];
  const label = (el) => el.textContent.replace(/\\s+/g, " ").trim().slice(0, 60);
  const lines = (el) => {
    const range = document.createRange();
    range.selectNodeContents(el);
    const rows = new Map();
    for (const r of range.getClientRects()) {
      if (r.width < 1) continue;
      const key = Math.round(r.top);
      const row = rows.get(key) || { left: Infinity, right: -Infinity };
      row.left = Math.min(row.left, r.left);
      row.right = Math.max(row.right, r.right);
      rows.set(key, row);
    }
    return [...rows.entries()].sort((a, b) => a[0] - b[0]).map(([, r]) => r);
  };
  for (const el of document.querySelectorAll(".sheet li, .sheet .rows p, .sheet dd, .subtitle")) {
    const rows = lines(el);
    const max = Number(el.dataset.maxLines || 0);
    if (max && rows.length > max) {
      problems.push(`"${label(el)}..." takes ${rows.length} lines; it may take ${max}.`);
    }
    if (rows.length > 1) {
      const width = el.getBoundingClientRect().width;
      const last = rows[rows.length - 1];
      if ((last.right - last.left) < width * %(min_last_line)s) {
        problems.push(`"${label(el)}..." ends with a very short last line (a widow).`);
      }
    }
  }
  document.documentElement.setAttribute("data-layout-report", JSON.stringify(problems));
})();
</script>
"""


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


def run_browser(*args: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as profile:
        return subprocess.run(
            [
                find_browser(),
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--hide-scrollbars",
                f"--user-data-dir={profile}",
                *args,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )


def count_pages(pdf: Path) -> int:
    """Count pages in a PDF written by Chrome (uncompressed page objects)."""
    return len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", pdf.read_bytes()))


def check_source(page: str) -> list[str]:
    """Rules that can be checked by reading index.html."""
    problems = []
    style = "\n".join(re.findall(r"<style>(.*?)</style>", page, re.DOTALL))
    for color in re.findall(r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)", style):
        if color.lower() not in ALLOWED_COLORS:
            problems.append(f"The stylesheet uses the color {color}; only black and white are allowed.")
    text = re.sub(r"<[^>]+>", " ", re.sub(r"<style>.*?</style>", " ", page, flags=re.DOTALL))
    for word in BANNED_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", text):
            problems.append(f'The CV names "{word}"; describe the capability instead of the board.')
    return problems


def check_layout(page: str) -> list[str]:
    """Rules that need the rendered page: line budgets and widows."""
    probe = LAYOUT_PROBE.replace("%(min_last_line)s", str(MIN_LAST_LINE))
    with tempfile.TemporaryDirectory() as folder:
        copy = Path(folder) / "index.html"
        copy.write_text(page.replace("</body>", probe + "</body>"), encoding="utf-8")
        result = run_browser(f"--window-size={A4_WINDOW}", "--dump-dom", copy.as_uri())
    match = re.search(r'data-layout-report="([^"]*)"', result.stdout)
    if not match:
        return [f"The layout check could not run:\n{result.stderr.strip()}"]
    return json.loads(html.unescape(match.group(1)))


def check(write_pdf: bool) -> None:
    page = HTML_FILE.read_text(encoding="utf-8")
    problems = check_source(page) + check_layout(page)

    with tempfile.TemporaryDirectory() as folder:
        target = PDF_FILE if write_pdf else Path(folder) / PDF_FILE.name
        result = run_browser("--no-pdf-header-footer", f"--print-to-pdf={target}", HTML_FILE.as_uri())
        if result.returncode != 0 or not target.is_file():
            problems.append(f"The browser could not print the PDF:\n{result.stderr.strip()}")
        else:
            pages = count_pages(target)
            if pages != 1:
                problems.append(f"The PDF has {pages} pages; it must fit on one.")

    if problems:
        print("The CV breaks the rules in STYLE.md:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        sys.exit(1)
    print(f"{'Built' if write_pdf else 'Checked'} {PDF_FILE.name}: 1 page, all checks pass.")


def fetch(source: str) -> str | None:
    """Read a URL or local file. Returns None if it doesn't exist."""
    if source.startswith(("http://", "https://")):
        try:
            with urllib.request.urlopen(source, timeout=30) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            raise
    path = Path(source)
    return path.read_text(encoding="utf-8") if path.is_file() else None


def validate(field: Field, text: str) -> str | None:
    """Return a problem with synced text, or None if it follows STYLE.md."""
    if not text:
        return "it is empty"
    if len(text) > field.max_chars:
        return f"it has {len(text)} characters; the limit is {field.max_chars}"
    if re.search(r"[<>*_`#\[\]]", text):
        return "it contains Markdown or HTML characters; use plain text"
    if field.sentence and not text.endswith("."):
        return "it must end with a full stop"
    if not field.sentence and text.endswith("."):
        return "it is a list and must not end with a full stop"
    if not text[0].isupper():
        return "it must start with a capital letter"
    return None


def sync(base: str) -> None:
    page = original = HTML_FILE.read_text(encoding="utf-8")
    for field in FIELDS:
        source = base.rstrip("/") + "/" + field.source if base.startswith("http") else str(
            Path(base) / field.source
        )
        raw = fetch(source)
        if raw is None:
            print(f"{field.source}: not published yet, so the CV keeps its current text.")
            continue
        text = " ".join(raw.split())
        problem = validate(field, text)
        if problem:
            sys.exit(f"{field.source}: {problem}. Fix it in open-conqueror. The CV is unchanged.")
        markers = re.compile(
            rf"(<!-- {re.escape(field.marker)}:start -->)(.*?)(<!-- {re.escape(field.marker)}:end -->)",
            re.DOTALL,
        )
        if not markers.search(page):
            sys.exit(f"index.html has no {field.marker} markers.")
        escaped = html.escape(text, quote=False)
        page = markers.sub(lambda m: f"{m.group(1)}{escaped}{m.group(3)}", page, count=1)

    if page == original:
        print("The synced text is already current.")
        return
    HTML_FILE.write_text(page, encoding="utf-8", newline="\n")
    print("Updated index.html from open-conqueror. Run build to check that it still fits.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="print index.html to the PDF and run every check")
    sub.add_parser("check", help="run the checks without writing the PDF")
    sync_parser = sub.add_parser("sync", help="copy open-conqueror's CV text into index.html")
    sync_parser.add_argument(
        "--from",
        dest="base",
        default=SOURCE_BASE,
        help="open-conqueror's raw URL or a local checkout (default: GitHub main)",
    )
    args = parser.parse_args()
    if args.command == "sync":
        sync(args.base)
    else:
        check(write_pdf=args.command == "build")


if __name__ == "__main__":
    main()
