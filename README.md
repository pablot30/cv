# CV – Pablo Torres

A one-page CV, written as a single HTML file and printed to PDF with a
Chromium-based browser. It is published at <https://pablot30.github.io/cv/>.

| File | What it is |
| --- | --- |
| `index.html` | The CV: content and styling in one file. Edit this one. |
| `data/open-conqueror-summary.txt` | The side project's "So far." line. Edit it here, not in `index.html`. |
| `data/open-conqueror-progress.json` | What the weekly check last saw of open-conqueror. Written by the workflow. |
| `Pablo-Torres-CV.pdf` | The PDF built from it. Rebuild it, don't edit it. |
| `STYLE.md` | The rules that keep the CV readable, consistent and on one page. |
| `scripts/cv.py` | Builds the PDF, checks the rules and watches open-conqueror's progress. |
| `.github/workflows/cv.yml` | Builds, checks and publishes the CV on GitHub, and runs the weekly check. |

## Requirements

Python 3.9 or newer, and any Chromium-based browser: Chrome, Edge, Brave or
Chromium. The script uses only Python's standard library, so there is nothing
else to install. If the browser is somewhere unusual, set `CV_BROWSER` to its
path.

The page uses Arial (macOS, Windows) or Liberation Sans (Linux). The two have
the same metrics, so lines break in the same places on all three systems. On
Linux, install `fonts-liberation` (Debian, Ubuntu) or `liberation-fonts`
(Fedora, Arch) if it isn't there already.

## Edit and build

Read [STYLE.md](STYLE.md) first. Then change the text in `index.html`, preview
it in a browser, and run this from this folder, on any system:

```sh
python scripts/cv.py build
```

On Windows, use `py` instead of `python` if that is how Python is installed.

`build` first copies the line in `data/open-conqueror-summary.txt` into
`index.html`, then prints the PDF and checks it against the rules: one page,
black and white only, no board names, no very short last lines (widows), and line budgets
for the synced text. If a check fails, it says which line breaks which rule.
Fix the wording rather than shrinking the font. `python scripts/cv.py check`
runs the same checks without changing any file, and also fails if `index.html`
doesn't match the file in `data/`.

Pushing to `main` publishes the change: the workflow runs the same build and
checks, then deploys the page and the PDF to GitHub Pages. If a check fails,
nothing is published.

## The open-conqueror line

The "So far." bullet of the side project lives in
`data/open-conqueror-summary.txt`: one line of plain text, at most 260
characters, with the rules in [STYLE.md](STYLE.md#the-open-conqueror-line).
open-conqueror itself knows nothing about this CV.

So that the line doesn't fall behind, the workflow looks at
[open-conqueror](https://github.com/pablot30/open-conqueror) every Monday. It
reads only what the project publishes for its own sake, anonymously: its GitHub
releases and tags, the table of finished increments in
`docs/test-reports/README.md`, and the "Current stage" line of
`docs/roadmap.md`. It compares them with `data/open-conqueror-progress.json`.
If something changed, it opens an issue labelled `cv-review` (or comments on
the one still open) listing what changed, with links, and then stores what it
saw. It never edits the CV text. If open-conqueror can't be read, or a file
changed its format, the log shows a warning, the stored state stays as it was,
and the CV is built and published as usual. Run it by hand from the Actions
tab at any time.

When a `cv-review` issue appears: read the linked changes, and if the line no
longer matches the finished work, edit `data/open-conqueror-summary.txt`, run
`python scripts/cv.py build`, and push. Close the issue either way.

The "AI development tools" skills row is still copied from
`docs/cv-ai-tools.txt` in open-conqueror, if that file exists, by
`python scripts/cv.py sync` (also run weekly; it keeps the current text if the
file is missing or can't be read). To try a version from a local checkout:
`python scripts/cv.py sync --from ../open-conqueror`.

If a line breaks a rule, or the CV no longer fits on one page, the workflow
fails, GitHub emails you, and the published CV stays as it was.

GitHub pauses scheduled workflows in a repository with no activity for 60 days.
If that happens, re-enable the workflow from the Actions tab.

## What is tracked

This folder also holds private documents, so `.gitignore` ignores everything
except the files listed in it. A new file is tracked only after you add it
there.
