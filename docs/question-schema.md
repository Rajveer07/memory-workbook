# Content schema — version 1

The catalog, knowledge units and question banks are JSON files independent of UI code. All source pages refer to physical PDF pages, not restarted printed slide numbers.

## Catalog

`catalog.json`: `schema_version`, `bank_version`, `subjects`, `sources`, `chapters`.

- Subject: `id`, `title`.
- Source: `id`, `title`, `private_filename`, `page_count`. A private filename is a basename inside ignored `sources/`.
- Chapter: `id`, `number`, `subject_id`, `source_id`, `title`, `page_start`, `page_end`, `bank_file`, `units_file`. Content filenames are basenames in `questions/`.

## Knowledge unit

Each unit contains `id`, `chapter_id`, `title`, `source_pages`, `kind`, `recall_points`, `importance` and `related_unit_ids`.

A unit is a meaningful concept, mechanism, list, quantitative cluster, institution, example or synthesis. It can span pages. Related-unit links are reserved for explicitly supported relationships; cross-page/chapter questions may instead cite their integrated synthesis unit. Private evidence extracts remain under ignored `private/`.

## Question

```json
{
  "id": "population-q001",
  "revision": 1,
  "chapter_id": "population",
  "unit_ids": ["population-u001"],
  "source_pages": [40],
  "scope": "unit",
  "format": "recall",
  "category": "keywords",
  "importance": "high",
  "tags": ["Population chapter architecture"],
  "quick_recall": false,
  "prompt": "Recall the population chapter’s main sections.",
  "expected_answer": {
    "style": "chain",
    "items": ["Introduction/theories → growth determinants → structure and trends → distribution → effects → measures/models → way forward"]
  },
  "source_note": ""
}
```

- `scope`: `unit` or `chapter`.
- `format`: `recall` or `fill_blank`.
- `category`: `concept`, `keywords`, `reasoning`, `relationship`, `list`, `data`, `institution` or `synthesis`.
- `importance`: `high` or `standard`.
- `expected_answer.style`: `definition`, `bullets` or `chain`; `items` is an array of concise text. The initial bank uses bullets/chains rather than answer tables.
- `source_note`: attribution limits, projections, source discrepancies or proposal status when needed.

A category describes what is being retrieved; format describes its UI. Thus legal-article blanks have category `institution`, while statistical blanks normally have category `data`. Data Drill selects `fill_blank` across both. Institutions includes dedicated institutional questions and report-attributed prompts. Quick Recall is explicitly annotated.

The server adds display-only `chapter_number`, `chapter_title`, `subject_id`, `source_id` and `institution` fields when loading. Content is rendered as text, never trusted HTML.

### Fill-in fields

```json
{
  "format": "fill_blank",
  "category": "data",
  "prompt": "NFHS-6 (2023–24), page 43: India’s TFR is {{b1}} children per woman.",
  "blanks": [
    {
      "id": "b1",
      "answer": "2.0",
      "accepted_answers": [],
      "label": "Blank 1",
      "input_mode": "decimal"
    }
  ],
  "expected_answer": {"style": "bullets", "items": ["2.0"]}
}
```

Every token matches one blank record. Multiple blanks retain context and are independently checkable/revealable. Units are displayed in the surrounding prompt. Numeric formatting equivalence is supported; text equivalence requires authored aliases. Matching is feedback only: the learner chooses their rating.

Preserve data ↔ indicator ↔ source ↔ time period wherever supplied. Do not invent missing attribution or dates. Integrated chapter recall may include data anchors in concise normal recall, while exact-value practice is available separately in Data Drill.

## SQLite state

`instance/progress.sqlite3` contains:

- `progress`: `question_id` primary key, `revision`, JSON-encoded `draft`, `bookmarked`, nullable `rating`, `good_streak`, `last_attempt_at`, `due_at`.
- `attempts`: ID, `question_id`, `revision`, `attempted_at`, `rating`, JSON-encoded `response`.

Rating changes and attempt insertion share one transaction. Drafts are strings for normal recall and blank-ID maps for fill-in questions. UTC ISO timestamps are used. A changed question revision keeps bookmarks and history but resets mastery and old drafts until reattempted.

## Validation and page audit

Check unique IDs, catalog links, existing knowledge units, nonempty answers, allowed enum values, source-page bounds and blank-token consistency. Unit questions remain inside their chapter’s pages; chapter synthesis can cite cross-chapter pages from the same source, but must include pages from its primary chapter.

`page-audit.json` records `page`, `chapter_id`, text/visual review status, linked unit/question IDs and inspection/omission notes. Audit coverage is not a mandate to turn every sentence or decorative element into a card. Current review includes all 72 pages, embedded image-only material, repeated slides and explicitly noted discrepancies.
