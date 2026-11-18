# CV style rules

These rules keep the CV readable, consistent and professional as it changes,
whether a person edits it or the weekly sync does. `python scripts/cv.py build`
checks the ones marked **(checked)**, and the publish workflow stops if any of
them fail.

## Layout

- **One A4 page.** **(checked)** Never shrink the font or margins to make
  something fit. Shorten or remove a line instead.
- **Black and white only.** **(checked)** Text, rules and links are black on
  white. No colors, photos or icons.
- **One font family:** Arial, or Liberation Sans on Linux (same metrics).
- **No widows.** **(checked)** The last line of a bullet, award or skills row
  must hold more than a word or two. Rephrase, or keep the last words together
  with `&nbsp;` or `<span class="nw">…</span>`.
- **Line budgets.** **(checked)** Text filled in from a file has a fixed
  number of lines (the `data-max-lines` attribute in `index.html`), so new text
  can never push the page over.
- **Keep names and numbers together** on one line: `860&nbsp;kW`,
  `GT&nbsp;SUV`, `CONCEPT AMG GT XX`.

## Structure

- **Section order:** Experience, Education, Awards, Skills, Side Project.
- **Experience:** newest first. At most three bullets for the current role, one
  or two for earlier ones.
- **Separators:** `·` between parts of a line, `–` (en dash) in date ranges,
  for example `2022 – Present`.
- **Dates:** years only.
- **Awards and education:** bold title · detail · year, with the detail in
  lowercase.
- **Skills:** a bold label and a comma-separated list, no full stop. Write a
  term out in full once with its abbreviation, such as "battery management
  systems (BMS)", so that both people and keyword filters find it.

## Wording

- **Plain, direct English**, the way you'd explain it to a colleague. Avoid
  marketing words and stiff phrases ("doubles as", "spearheaded", "leveraged",
  "cutting-edge", "passionate", "synergy").
- **No "I" at the start of a bullet.** Start with a verb: present tense for the
  current role ("Develop", "Validate"), past tense for finished work ("Built",
  "Defined").
- **Credit the team honestly.** Use "Contributed" for team results, and only
  claim personal work as your own.
- **Only finished, verifiable work.** Plans go in the Vision bullet, never in
  "So far". A patent is "patent-pending" until it's granted.
- **General, not gadget lists.** **(checked)** No specific microcontroller
  boards (Arduino, ESP32, UNO); name the capability instead.
- **Numbers that matter:** at most one or two per bullet, each one checked
  against a public source.

## The open-conqueror line

The "So far." bullet comes from `data/open-conqueror-summary.txt`, which
`build` copies into `index.html`. It is one line of plain text, no Markdown or
HTML, at most 260 characters and 2 printed lines. One sentence, past tense,
starting with a verb and ending with a full stop. Finished work only: "built",
not "shipped", until open-conqueror has a release. **(checked:** length, full
stop, capital letter, plain text, line budget, no board names**)**

Review it whenever the weekly check opens a `cv-review` issue (see the README).

## Synced text from open-conqueror

The "AI development tools" skills row comes from `docs/cv-ai-tools.txt` in the
[open-conqueror](https://github.com/pablot30/open-conqueror) repository, if it
exists: a comma-separated list of tools and practices actually in use, plain
text, no full stop, at most 1 printed line. If the file is missing or can't be
read, the CV keeps its current text. **(checked)** The sync refuses text with
Markdown or HTML characters, and checks the full stop rule.
