# CV – Pablo Torres

A one-page CV, written as a single HTML file and printed to PDF with a
Chromium-based browser. It is published at <https://pablot30.github.io/cv/>.

| File | What it is |
| --- | --- |
| `index.html` | The CV: content and styling in one file. Edit this one. |
| `Pablo-Torres-CV.pdf` | The PDF built from it. Rebuild it, don't edit it. |
| `STYLE.md` | The rules that keep the CV readable, consistent and on one page. |
| `scripts/cv.py` | Builds the PDF, checks the rules and syncs text from open-conqueror. |
| `.github/workflows/cv.yml` | Builds, checks and publishes the CV on GitHub. |

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

`build` prints the PDF and checks it against the rules: one page, black and
white only, no board names, no very short last lines (widows), and line budgets
for the synced text. If a check fails, it says which line breaks which rule.
Fix the wording rather than shrinking the font. `python scripts/cv.py check`
runs the same checks without changing the PDF.

Pushing to `main` publishes the change: the workflow runs the same build and
checks, then deploys the page and the PDF to GitHub Pages. If a check fails,
nothing is published.

## Text synced from open-conqueror

Two parts of the CV aren't written here. They come from plain-text files in
the [open-conqueror](https://github.com/pablot30/open-conqueror) repository, so
they're updated together with the project:

| File in open-conqueror | Fills in |
| --- | --- |
| `docs/cv-summary.txt` | the "So far." bullet of the side project |
| `docs/cv-ai-tools.txt` | the "AI development tools" skills row |

The rules for both files are in [STYLE.md](STYLE.md#synced-text-from-open-conqueror).
A file that doesn't exist yet leaves its part of the CV as it is.

Every Monday the workflow copies both files into `index.html` between their
markers (`<!-- so-far:start -->` and `<!-- ai-tools:start -->`), runs the
build and checks, commits if anything changed, and redeploys. To update the CV
straight away, run the workflow by hand from the Actions tab, or locally:

```sh
python scripts/cv.py sync
python scripts/cv.py build
```

To try text before it's merged in open-conqueror, point the sync at a local
checkout: `python scripts/cv.py sync --from ../open-conqueror`.

If the synced text breaks a rule, or the CV no longer fits on one page, the
workflow fails, GitHub emails you, and the published CV stays as it was.

GitHub pauses scheduled workflows in a repository with no activity for 60 days.
If that happens, re-enable the workflow from the Actions tab.

## What is tracked

This folder also holds private documents, so `.gitignore` ignores everything
except the files listed in it. A new file is tracked only after you add it
there.
