# CV – Pablo Torres

A one-page CV, written as a single HTML file and printed to PDF with a
Chromium-based browser. It is published at <https://pablot30.github.io/cv/>.

| File | What it is |
| --- | --- |
| `index.html` | The CV: content and styling in one file. Edit this one. |
| `Pablo-Torres-CV.pdf` | The PDF built from it. Rebuild it, don't edit it. |
| `scripts/cv.py` | Builds the PDF and syncs the side-project progress line. |
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

Change the text in `index.html` and preview it in a browser. Then, from this
folder, on any system:

```sh
python scripts/cv.py build
```

On Windows, use `py` instead of `python` if that is how Python is installed.

The command prints the PDF and fails if it doesn't fit on one A4 page. If that
happens, shorten a bullet rather than shrinking the font.

Pushing to `main` publishes the change: the workflow rebuilds the PDF, checks
the page count and deploys both files to GitHub Pages.

## The side-project progress line

The "So far" bullet under open-conqueror isn't written here. It comes from
[`docs/cv-summary.txt`](https://github.com/pablot30/open-conqueror/blob/main/docs/cv-summary.txt)
in the open-conqueror repository, so it's updated together with the project.
The file holds one line of plain text, at most 260 characters.

Every Monday, the workflow copies that line into `index.html` between the
`so-far` markers, rebuilds the PDF, commits both if the text changed, and
redeploys. To update the CV straight away instead, run the workflow by hand
from the Actions tab, or locally:

```sh
python scripts/cv.py sync
python scripts/cv.py build
```

If the summary is too long, or the CV no longer fits on one page, the workflow
fails, GitHub emails you, and the published CV stays as it was.

GitHub pauses scheduled workflows in a repository with no activity for 60 days.
If that happens, re-enable the workflow from the Actions tab.

## What is tracked

This folder also holds private documents, so `.gitignore` ignores everything
except the files listed in it. A new file is tracked only after you add it
there.
