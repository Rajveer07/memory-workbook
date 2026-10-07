# UPSC Memory Workbook

A standalone personal study notebook for **active recall and memorisation** of UPSC material. Retrieve concepts, terminology, data, causes, consequences and chapter logic before revealing the expected recall. Full answer-writing practice belongs on paper; this application has no essay scoring or AI evaluation.

**Recall → reveal → self-evaluate → revisit weak knowledge.**

## Included source coverage

The supplied 72-page PDF was opened, text-extracted, rendered and visually inspected page by page, including embedded charts, tables, diagrams, footnotes and captions.

| Workbook chapter | Physical PDF pages | Questions |
| --- | --- | ---: |
| Role of Women and Women’s Organisations | 1–39 | 172 |
| Population and Associated Issues | 40–72 | 161 |
| **Total** | **72 pages** | **333** |

The bank contains **72 knowledge units**, **145 fill-in-the-blank questions**, **63 reasoning/relationship questions**, and **18 chapter-level reconstruction questions**. Chapter questions appear after ordinary recall in each chapter. Cross-chapter synthesis retains all contributing physical PDF pages. The PDF’s printed chapter numbering and restarted slide numbers are not used as workbook page references.

Content stays grounded in the supplied PDF. It is a source-retrieval workbook, not an independently updated factual reference. Different source figures, chart/text discrepancies, projections, targets, proposals and reported policy status retain their own context and notes. Decorative logos, photo credits and the unrelated meme’s app-download/rating trivia are not converted into recall questions. Repeated slides are merged into shared units.

## Features

- **Learn:** all questions in source order.
- **Weak:** Again/Hard questions, with due items first and shorter retries for Again.
- **Quick Recall:** definitions, keywords and compact factual retrieval.
- **Data Drill:** fill-in questions, including quantitative legal and policy references.
- **Concepts & Reasoning:** concepts, why/how prompts and relationships.
- **Institutions:** committees, reports, organisations, Acts, Articles and schemes.
- **Chapter Recall:** integrated architecture, reasoning and connections.
- **Bookmarked:** a personal last-minute revision collection.
- Compact multiple-blank inputs, separate checking/revealing and reveal-all.
- Concise bullets and arrow chains; no multiple-choice guessing or AI grading.
- Global search across prompts, answers, terms and report context, regardless of the current chapter/page/mode filter.
- Chapter mastery counts: Strong, Hard, Weak and Unseen. Viewing/revealing does not count as mastery.
- SQLite response drafts, bookmarks, ratings, review dates and complete rated-attempt history.
- Private local PDF source links, dark mode, responsive layout and keyboard-accessible controls.
- JSON progress export and no authentication setup for local personal use.

## Screenshots

_Placeholder: add desktop recall, multi-blank Data Drill and mobile screenshots under `docs/screenshots/` after running the application._

## Installation

Requires **Python 3.10 or later**. No Node, frontend build process, cloud database or external API is required.

```bash
cd upsc-memory-workbook
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

Open **http://127.0.0.1:5000**. The server binds to localhost and creates `instance/progress.sqlite3` and an ignored local session key on first run. Stop with `Ctrl+C`. If your OS needs a separate Python virtual-environment package, install that package through your normal system setup first.

The current workspace already has an ignored `.venv` with the required packages available, so you can run:

```bash
cd upsc-memory-workbook
.venv/bin/python run.py
```

### Private source placement

Keep your PDF at:

```text
sources/Indian Society Lecture 03 PPT (1).pdf
```

`questions/catalog.json` maps its source ID to that private filename. The PDF is served only by the local Flask application. Questions work even if the PDF is absent; View Source then explains how to restore it. PDF viewers generally honour the physical `#page=N` fragment; mobile viewers may require manual page navigation.

The `.gitignore` explicitly includes:

```gitignore
sources/*.pdf
```

It also excludes all PDFs, private extracts/renders, virtual environments, local databases, session keys, secrets, logs and caches. Source-derived question banks and their authoring script are separate from the private PDF; review their publication suitability before pushing a public repository.

## Daily use

1. Choose a subject, chapter and optional physical PDF page.
2. Choose a revision mode.
3. Retrieve your answer in keywords, bullets or a short reasoning chain. For data, fill compact blanks.
4. Reveal and compare with expected recall. Individual blank matching is convenience feedback, not grading.
5. Mark **Again**, **Hard** or **Good**. Rating saves an attempt and advances immediately.
6. Revisit Weak and finish with Chapter Recall.

Blank matching ignores case, surrounding whitespace and en-dash versus hyphen. Numeric blanks accept equivalent decimal formatting and commas (`40`/`40.0`, `100116`/`1,00,116`). Text aliases are explicitly authored; it does not guess semantic equivalence. Rate yourself after comparing.

Drafts autosave while typing and when navigating. Save failures are shown and failed ratings do not advance. Bookmarks and responses survive restarting the server and opening another browser on the same local server because they live in SQLite. Dark-mode preference alone lives in browser storage.

### Lightweight scheduling

| Latest rating | Mastery | Next review |
| --- | --- | --- |
| None | Unseen | No attempted rating |
| Again | Weak | 10 minutes; shorter in-session Weak retry |
| Hard | Hard | 1 day; longer in-session Weak retry |
| Good | Strong | Consecutive Good: 3, 7, 14, then 30 days |

Again/Hard reset the Good sequence. Weak still lets you practise all difficult questions before their due date, but orders due questions first. When enough intervening cards remain, Again repeats after three cards and Hard after eight. Small pools wait for your next revision pass. Good removes later copies from a Weak queue. Learn keeps normal source order; the scheduler never hides questions from it.

“Strong” reflects your latest Good self-rating, not proof of permanent retention. Due counts show when rated material should be revisited.

## Project structure

```text
upsc-memory-workbook/
├── app/
│   ├── __init__.py          Flask routes, local source access, request validation
│   ├── content.py           Schema/link validation, search and mode rules
│   └── progress.py          SQLite state, attempt history, scheduling
├── static/                  Vanilla JavaScript, CSS, SVG favicon
├── templates/               Jinja2 workbook and missing-source page
├── questions/
│   ├── catalog.json         Subjects, chapters and private source mappings
│   ├── women.json           Women question bank
│   ├── women-units.json     Women knowledge units
│   ├── population.json      Population question bank
│   ├── population-units.json
│   └── page-audit.json      All 72 pages, inspection notes and content links
├── scripts/
│   ├── build_bank.py        Manually authored source-reviewed bank builder
│   ├── validate_bank.py     Provenance, blank and page-coverage validation
│   └── inspect_pdf.py       Optional private extraction and rendering
├── tests/                   Content, modes, persistence, scheduling and routes
├── docs/                    Architecture, schema and source-review notes
├── sources/                 Private PDF (ignored)
├── private/                 Working extracts and page images (ignored)
├── instance/                SQLite database and session key (ignored)
├── requirements.txt         Runtime: Flask (Jinja2 included)
├── requirements-analysis.txt  Optional PDF inspection dependencies
├── run.py
└── .gitignore
```

## How question data is organised

See [the question schema](docs/question-schema.md). Each question has a stable ID and content revision, chapter ID, physical source pages, knowledge-unit IDs, scope, category, importance, prompt, concise expected answer and optional source note. Fill-in questions use named tokens mapped to individual blank records. Lists remain one reconstruction prompt; concepts spanning pages remain shared units.

`page-audit.json` links each inspected page to knowledge units and questions. Inspection flags document the completed manual review; software coverage checks cannot replace visual reading.

The app loads JSON banks from the catalog. It does not depend on `build_bank.py` to run. That script is the reproducible authoring record for this initial bank. If you edit its output JSON directly, do not rerun the builder unless those edits have also been transferred to the script.

## Add another chapter, book or subject

1. Keep the new PDF under ignored `sources/`.
2. Register a source and subject (if new) in `questions/catalog.json`.
3. Add a chapter record with its ID, display number, subject/source IDs, physical page boundaries and bank/unit filenames.
4. Inspect every page and extract meaningful units before authoring questions. Include reasoning and source-qualified quantitative blanks; never use external facts to silently fix the source.
5. Write the chapter’s unit and question JSON using the documented schema. Append chapter synthesis after ordinary source-order questions.
6. Use stable IDs. Increment a question’s `revision` when materially changing its prompt/answer. Revised cards retain bookmarks/history but reset mastery and old drafts.
7. Run the content validator and restart Flask.

The UI, global search and mastery summaries come from catalog data and do not require changes for additional chapters. The initial PDF-specific page-audit script/test assertions should be extended when auditing another source; the runtime schema validator already supports arbitrary catalog sources.

Optional extraction tooling:

```bash
python -m pip install -r requirements-analysis.txt
python scripts/inspect_pdf.py "sources/Indian Society Lecture 03 PPT (1).pdf" \
  --expected-pages 72 --output private/inspection
```

This only extracts and renders; it never invents questions or marks pages as manually inspected.

## Validation

```bash
python scripts/validate_bank.py
python -m unittest discover -s tests -v
```

The initial implementation passes 12 tests covering the complete bank/audit, image-only content, each revision mode, cross-chapter search, draft persistence, rating history, mastery, repeat intervals, multiple-blank state, changed content revisions, source-file range access, export and mutation validation.

The build sandbox prohibits listening sockets, so starting the local Flask server here raises `PermissionError: [Errno 1] Operation not permitted`. Run the commands above from your normal terminal. Routes and persistence were verified through Flask's test client without a listening server. No browser automation was available; desktop/mobile layouts and controls are implemented but have not been visually tested in a live browser. The screenshot area above is intentionally a placeholder. Tests use a synthetic source-route fixture and do not require the private PDF.

## Progress backup

Use **Back up progress** to download a JSON snapshot of state and attempt history. For an exact restorable backup, stop Flask and copy `instance/progress.sqlite3` to a private backup location. Restore by stopping Flask and replacing that database file. Do not commit personal backups. JSON export is for portability/inspection; automatic JSON import is not implemented.

## Initialise and push to GitHub

Run these commands **inside this new project directory**, so it becomes its own repository:

```bash
git init
git status --short --ignored
git check-ignore "sources/Indian Society Lecture 03 PPT (1).pdf"
git add .
git diff --cached --stat
git commit -m "Initial UPSC Memory Workbook"
git branch -M main
git remote add origin <repository-url>
git push -u origin main
```

Create an empty GitHub repository first and replace `<repository-url>`. Inspect staged files before committing; no PDF, `instance/`, `.venv/`, `private/` or secret file should be staged. If a private file was already tracked elsewhere, ignore rules do not untrack it automatically. This project has not been committed, pushed or publicly deployed.
