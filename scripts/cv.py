#!/usr/bin/env python3
"""Build the CV PDF, check it against STYLE.md, and keep an eye on open-conqueror.

Usage (from the repository root, on macOS, Linux or Windows):

    python scripts/cv.py build    Fill in index.html from data/, print the PDF, run every check.
    python scripts/cv.py check    Run the checks without changing any file.
    python scripts/cv.py sync     Copy open-conqueror's AI tools list into index.html.
    python scripts/cv.py watch    Compare open-conqueror's releases, tags, test reports
                                  and roadmap stage with data/open-conqueror-progress.json.

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

DATA_DIR = ROOT / "data"
STATE_FILE = DATA_DIR / "open-conqueror-progress.json"

OC_REPO = "pablot30/open-conqueror"
OC_WEB = f"https://github.com/{OC_REPO}"
OC_API = f"https://api.github.com/repos/{OC_REPO}"
SOURCE_BASE = f"https://raw.githubusercontent.com/{OC_REPO}/main/"


@dataclass(frozen=True)
class Field:
    """A piece of the CV that is filled in from a plain-text file."""

    marker: str  # name of the <!-- name:start --> ... <!-- name:end --> markers
    source: str  # path of the plain-text file (here in data/, or in open-conqueror)
    max_chars: int  # a quick first limit; the real limit is data-max-lines
    sentence: bool  # True: must end with a full stop. False: must not.


# Kept in this repository and filled in by every build.
LOCAL_FIELDS = (Field("so-far", "data/open-conqueror-summary.txt", 260, sentence=True),)
# Copied from open-conqueror by `sync`.
FIELDS = (Field("ai-tools", "docs/cv-ai-tools.txt", 100, sentence=False),)

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


def fill(page: str, field: Field, text: str) -> str:
    """Put text between the field's markers in page."""
    markers = re.compile(
        rf"(<!-- {re.escape(field.marker)}:start -->)(.*?)(<!-- {re.escape(field.marker)}:end -->)",
        re.DOTALL,
    )
    if not markers.search(page):
        sys.exit(f"index.html has no {field.marker} markers.")
    escaped = html.escape(text, quote=False)
    return markers.sub(lambda m: f"{m.group(1)}{escaped}{m.group(3)}", page, count=1)


def fill_local(page: str) -> str:
    """Fill in the fields kept in data/, or exit if a file breaks STYLE.md."""
    for field in LOCAL_FIELDS:
        path = ROOT / field.source
        if not path.is_file():
            sys.exit(f"{field.source} is missing; it holds the CV's text for the {field.marker} markers.")
        raw = path.read_text(encoding="utf-8")
        if len(raw.strip().splitlines()) > 1:
            sys.exit(f"{field.source}: keep it on one line.")
        text = " ".join(raw.split())
        problem = validate(field, text)
        if problem:
            sys.exit(f"{field.source}: {problem}. The CV is unchanged.")
        page = fill(page, field, text)
    return page


def check(write_pdf: bool) -> None:
    page = HTML_FILE.read_text(encoding="utf-8")
    filled = fill_local(page)
    if filled != page:
        if not write_pdf:
            sources = ", ".join(field.source for field in LOCAL_FIELDS)
            sys.exit(f"index.html doesn't match {sources}. Run `python scripts/cv.py build`.")
        HTML_FILE.write_text(filled, encoding="utf-8", newline="\n")
        print(f"Filled in index.html from {', '.join(f.source for f in LOCAL_FIELDS)}.")
        page = filled
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


def warn(message: str) -> None:
    """Print a warning, shown as an annotation when running on GitHub Actions."""
    prefix = "::warning::" if os.environ.get("GITHUB_ACTIONS") == "true" else "Warning: "
    print(prefix + message)


def fetch(source: str) -> str | None:
    """Read a URL or local file. Returns None if it doesn't exist.

    URLs are read without credentials: open-conqueror is public.
    """
    if source.startswith(("http://", "https://")):
        request = urllib.request.Request(source, headers={"User-Agent": "cv-build"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
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
        try:
            raw = fetch(source)
        except (OSError, ValueError) as error:  # URLError, timeouts, bad encoding
            warn(f"{field.source}: could not be read ({error}), so the CV keeps its current text.")
            continue
        if raw is None:
            print(f"{field.source}: not published yet, so the CV keeps its current text.")
            continue
        text = " ".join(raw.split())
        problem = validate(field, text)
        if problem:
            sys.exit(f"{field.source}: {problem}. Fix it in open-conqueror. The CV is unchanged.")
        page = fill(page, field, text)

    if page == original:
        print("The synced text is already current.")
        return
    HTML_FILE.write_text(page, encoding="utf-8", newline="\n")
    print("Updated index.html from open-conqueror. Run build to check that it still fits.")


# --- watch: notice open-conqueror's progress and ask a person to review the CV line.
#
# Reads only what open-conqueror publishes for its own sake, without credentials,
# and never changes the CV text. Each signal is read on its own: if one can't be
# read, or its format changed, it keeps its stored value and a warning says why.


class Unreadable(Exception):
    """A signal could not be read or no longer has the expected format."""


def read_releases() -> list[str]:
    """Tag names of open-conqueror's published GitHub releases."""
    request = urllib.request.Request(
        f"{OC_API}/releases?per_page=100",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "cv-progress-check"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, list) or not all(isinstance(r, dict) and "tag_name" in r for r in data):
        raise Unreadable("the releases API answered in an unexpected format")
    return sorted(r["tag_name"] for r in data if not r.get("draft"))


def read_tags() -> list[str]:
    """open-conqueror's git tags, read with git so the API rate limit doesn't apply."""
    if not shutil.which("git"):
        raise Unreadable("git is not installed")
    result = subprocess.run(
        ["git", "ls-remote", "--tags", "--refs", f"{OC_WEB}.git"],
        # Outside this checkout, so a token that actions/checkout stored in its
        # git config is never sent: the read stays anonymous.
        cwd=tempfile.gettempdir(),
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise Unreadable(f"git ls-remote failed: {result.stderr.strip()}")
    return sorted(line.split("refs/tags/", 1)[1] for line in result.stdout.splitlines() if "refs/tags/" in line)


def cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def read_increments() -> tuple[list[dict], dict[str, str]]:
    """Rows of the table in docs/test-reports/README.md: one per finished increment.

    Returns the rows to store ({"report", "result"}) and a link for each report.
    """
    base = "docs/test-reports/"
    text = fetch(SOURCE_BASE + base + "README.md")
    if text is None:
        raise Unreadable(f"{base}README.md no longer exists")
    lines = text.splitlines()
    for i, line in enumerate(lines):
        head = [c.lower() for c in cells(line)] if line.lstrip().startswith("|") else []
        if head and head[0] == "report" and "result" in head:
            break
    else:
        raise Unreadable(f"{base}README.md has no table with Report and Result columns")
    result_col = head.index("result")
    if i + 1 >= len(lines) or not re.fullmatch(r"[\s|:-]+", lines[i + 1]):
        raise Unreadable(f"{base}README.md: the table has no header separator")
    rows, links = [], {}
    for line in lines[i + 2 :]:
        if not line.lstrip().startswith("|"):
            break
        row = cells(line)
        if len(row) != len(head):
            raise Unreadable(f"{base}README.md: a table row has {len(row)} cells, the header {len(head)}")
        match = re.fullmatch(r"\[(.+?)\]\((.+?)\)", row[0])
        report = match.group(1) if match else row[0]
        if match:
            target = match.group(2)
            links[report] = target if target.startswith("http") else f"{OC_WEB}/blob/main/{base}{target}"
        rows.append({"report": report, "result": row[result_col]})
    return rows, links


def read_stage() -> str:
    """The **Current stage: ...** line at the top of docs/roadmap.md."""
    text = fetch(SOURCE_BASE + "docs/roadmap.md")
    if text is None:
        raise Unreadable("docs/roadmap.md no longer exists")
    match = re.search(r"^\*\*Current stage:\s*(.+?)\.?\*\*", text, re.MULTILINE)
    if not match:
        raise Unreadable("docs/roadmap.md has no **Current stage: ...** line")
    return match.group(1).strip()


def describe(key: str, old, new, links: dict[str, str]) -> list[str]:
    """Markdown list items that say what changed in one signal."""
    if key in ("releases", "tags"):
        kind = "release" if key == "releases" else "tag"
        url = f"{OC_WEB}/releases/tag/" if key == "releases" else f"{OC_WEB}/tree/"
        added = [f"- New {kind} [`{t}`]({url}{t})" for t in new if t not in old]
        gone = [f"- The {kind} `{t}` is gone ([all {key}]({OC_WEB}/{key}))" for t in old if t not in new]
        return added + gone
    if key == "increments":
        index = f"{OC_WEB}/blob/main/docs/test-reports/README.md"
        before = {row["report"]: row["result"] for row in old}
        after = {row["report"]: row["result"] for row in new}
        items = []
        for report, result in after.items():
            link = f"[{report}]({links.get(report, index)})"
            if report not in before:
                items.append(f"- New test report: {link}, result: {result}")
            elif before[report] != result:
                items.append(f"- Test report {link} changed from {before[report]} to {result}")
        items += [f"- The test report row \"{r}\" is gone ([test reports]({index}))" for r in before if r not in after]
        return items
    if key == "stage":
        return [f"- The [roadmap]({OC_WEB}/blob/main/docs/roadmap.md) stage changed from \"{old}\" to \"{new}\""]
    return [f"- {key} changed"]


def issue_body(changes: list[str]) -> str:
    field = LOCAL_FIELDS[0]
    line = " ".join((ROOT / field.source).read_text(encoding="utf-8").split())
    return "\n".join(
        [
            "open-conqueror has made progress since the CV's \"So far.\" line was last reviewed:",
            "",
            *changes,
            "",
            "The line in the CV now reads:",
            "",
            f"> {line}",
            "",
            "Please check it against open-conqueror's "
            f"[roadmap]({OC_WEB}/blob/main/docs/roadmap.md), "
            f"[journey]({OC_WEB}/blob/main/docs/journey.md) and "
            f"[test reports]({OC_WEB}/blob/main/docs/test-reports/README.md). "
            f"If it should change, edit `{field.source}` (rules in "
            f"[STYLE.md](https://github.com/{os.environ.get('GITHUB_REPOSITORY', 'pablot30/cv')}/blob/main/STYLE.md)), run `python scripts/cv.py build` and push. "
            "Close this issue once the line is right, whether or not it needed a change.",
            "",
            "_Opened by the weekly CV workflow. It only watches open-conqueror; it never changes the CV text._",
            "",
        ]
    )


def watch(body_file: Path | None) -> None:
    stored = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.is_file() else {}
    readers = {
        "releases": read_releases,
        "tags": read_tags,
        "increments": read_increments,
        "stage": read_stage,
    }
    current, links = {}, {}
    for key, reader in readers.items():
        try:
            value = reader()
        except (Unreadable, OSError, ValueError, subprocess.SubprocessError) as error:
            # OSError covers URLError, HTTPError and timeouts; ValueError bad JSON.
            warn(f"open-conqueror {key}: {error}. Kept the last known value; the CV is not affected.")
            current[key] = stored.get(key)
            continue
        if key == "increments":
            value, links = value
        current[key] = value
        print(f"open-conqueror {key}: {json.dumps(value)}")

    changes = []
    for key, value in current.items():
        old = stored.get(key)
        if old is None and value is not None:
            print(f"open-conqueror {key}: no earlier value stored, so this one becomes the baseline.")
        elif value is not None and value != old:
            changes += describe(key, old, value, links)

    if current != stored:
        STATE_FILE.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"Updated {STATE_FILE.relative_to(ROOT).as_posix()}.")
    if changes:
        print("Changes worth a look at the CV line:\n" + "\n".join(changes))
        if body_file:
            body_file.write_text(issue_body(changes), encoding="utf-8")
    else:
        print("No progress to review.")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"changed={'true' if changes else 'false'}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="fill in index.html from data/, print the PDF, run every check")
    sub.add_parser("check", help="run the checks without changing any file")
    sync_parser = sub.add_parser("sync", help="copy open-conqueror's AI tools list into index.html")
    sync_parser.add_argument(
        "--from",
        dest="base",
        default=SOURCE_BASE,
        help="open-conqueror's raw URL or a local checkout (default: GitHub main)",
    )
    watch_parser = sub.add_parser(
        "watch", help="compare open-conqueror's progress with data/open-conqueror-progress.json"
    )
    watch_parser.add_argument(
        "--issue-body", type=Path, help="if anything changed, write an issue text for a person here"
    )
    args = parser.parse_args()
    if args.command == "sync":
        sync(args.base)
    elif args.command == "watch":
        watch(args.issue_body)
    else:
        check(write_pdf=args.command == "build")


if __name__ == "__main__":
    main()
