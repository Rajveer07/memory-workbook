# UPSC Memory Workbook — implemented architecture

A standalone localhost application using Python, Flask, SQLite, Jinja2, semantic HTML/CSS and vanilla JavaScript. No connection to an existing website or remote service.

## Data flow

Private PDF → manual text and visual inspection → meaningful knowledge units → source-mapped JSON recall questions → Jinja2 shell/JavaScript study interface → self-ratings and response history in SQLite.

All 72 source pages have been inspected. The current catalog contains Society with two chapters: Women (physical PDF pages 1–39) and Population (40–72). The content bank has 72 units and 333 questions. Subject, chapter and source selectors are catalog-driven.

## Boundaries

- `app/content.py` reads and validates catalog, unit and question files. It implements search and mode predicates.
- `app/progress.py` owns SQLite transactions, progress/history and due dates. Connections commit/rollback and close deterministically.
- `app/__init__.py` exposes the workbook, filtered content, validated progress mutations, history, export and private source-file routes.
- `templates/` contains the Jinja2 interface; `static/` contains the study interaction and responsive notebook theme.
- `scripts/build_bank.py` is manually authored source content, not automated PDF question generation. The runtime uses its JSON outputs directly.
- `private/` contains working extracts/renders; `sources/` holds private PDFs. Both are ignored.

## Interaction and persistence

Normal recall uses a short textarea. Data/legal-number prompts use compact multiple-blank inputs with separate checks/reveals. Revealing alone never changes mastery. Again/Hard/Good ratings atomically save current recall, update mastery/scheduling and append an attempt. Draft/bookmark updates do not create attempts.

SQLite `progress` records are keyed by stable question ID and revision; `attempts` retains historical revision and response. The server stores state for a single personal learner. Dark-mode preference is the only localStorage value. No authentication is needed for the localhost-only default.

Learn uses source order, with chapter synthesis last. Weak prioritises due difficult questions, repeating Again sooner when enough intervening cards remain. Good intervals expand across 3/7/14/30 days. Global search deliberately overrides the current chapter, page and mode to find information throughout the workbook.

## Provenance and content review

Physical PDF pages are canonical. Cross-page units retain all relevant references, and chapter synthesis may connect material from both chapters. Sources missing dates remain undated; reports with differing figures stay distinguished. Proposal tables are labelled proposals; projections remain projections. Source errors/discrepancies are recorded rather than silently corrected with external content.

`questions/page-audit.json` records the completed text/visual review and coverage of all pages. The tests check links, mode behaviour, SQLite durability and scheduling. Browser rendering was not automatically tested because this environment has no browser automation runtime.

## Delivery

Run locally using `python run.py` from a normal terminal. This build sandbox prohibits listening sockets, so routes/persistence were verified with Flask's test client. The repo excludes sources, personal databases, virtual environments and private working files. README covers installation, extension, backup, validation and independent GitHub initialisation. The project is neither pushed nor published.
