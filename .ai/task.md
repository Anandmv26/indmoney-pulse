# INDmoney AI Workflow — Task Tracker

> **Last updated:** 2026-03-22
> **Status:** All phases complete ✅ Project finished.

---

## Legend

- ✅ Complete
- 🔲 Not started
- 🔄 In progress

---

## Phase 1 — Project Setup

| # | Task | Status |
|---|------|--------|
| 1.1 | Create project folder structure (all directories and `__init__.py` files) | ✅ |
| 1.2 | Create `requirements.txt` with: `google-play-scraper`, `google-genai`, `python-dotenv`, `pandas`, `flask` | ✅ |
| 1.3 | Create `.env.example` with placeholders for `GEMINI_API_KEY`, `GMAIL_MCP_URL`, `GDOC_MCP_URL`, `TARGET_DOC_ID`, `DRAFT_RECIPIENT` | ✅ |
| 1.4 | Create `.gitignore` (`.env`, `venv/`, `__pycache__/`, `data/raw/`, `data/processed/`, `outputs/`) | ✅ |
| 1.5 | Create virtual environment and install dependencies | ✅ |
| 1.6 | Create `.env` from `.env.example` and fill in real keys | 🔲 |

---

## Phase 2 — Scraper (`src/scraper/scraper.py`)

| # | Task | Status |
|---|------|--------|
| 2.1 | Define constants: `APP_ID`, `FETCH_COUNT=200`, `WEEKS_BACK=10`, `MIN_WORD_COUNT=10`, `OUTPUT_DIR` | ✅ |
| 2.2 | Implement `fetch_reviews(count)` — hard cap at 200, drop null/empty/whitespace/single-word reviews | ✅ |
| 2.3 | Implement `filter_by_date(reviews, weeks)` — drop reviews older than cutoff | ✅ |
| 2.4 | Implement `clean(reviews)` — drop `userName`, keep 4 columns, drop low-quality reviews, cap at 200 rows | ✅ |
| 2.5 | Implement `save_csv(df)` — save to `data/processed/indmoney_reviews_YYYY-MM-DD.csv` | ✅ |
| 2.6 | Implement `run()` — chain all functions, print progress, return CSV path | ✅ |
| 2.7 | Manual test: run scraper standalone and verify CSV output | ✅ |

---

## Phase 3 — Pulse Generator (`src/pulse/pulse_generator.py`)

| # | Task | Status |
|---|------|--------|
| 3.1 | Define constants: `MODEL`, `MAX_TOKENS=1500`, `MAX_NOTE_WORDS=250` | ✅ |
| 3.2 | Define prompt template (exact text from architecture) | ✅ |
| 3.3 | Implement `load_reviews(csv_path)` — read CSV, return list of review_text strings | ✅ |
| 3.4 | Implement `build_prompt(reviews)` — join reviews, substitute into template | ✅ |
| 3.5 | Implement `call_gemini(prompt)` — call Gemini API with `temperature=0` | ✅ |
| 3.6 | Implement `parse_response(raw)` — strip markdown fences, parse JSON | ✅ |
| 3.7 | Implement `validate(output)` — check themes ≤5, top_themes ==3, quotes ==3, actions ==3, truncate note to 250 words | ✅ |
| 3.8 | Implement `run(csv_path)` — chain all functions, print progress, return dict | ✅ |
| 3.9 | Manual test: run with real CSV and verify JSON output structure | ✅ |

---

## Phase 4 — Fee Explainer (`src/fee/fee_explainer.py`)

| # | Task | Status |
|---|------|--------|
| 4.1 | Define constants: `MODEL`, `MAX_TOKENS=800`, `FEE_SCENARIO`, `MAX_BULLETS=6`, `MIN_BULLETS=4`, `APPROVED_SOURCE_DOMAINS` | ✅ |
| 4.2 | Define prompt template (exact text from architecture) | ✅ |
| 4.3 | Define `FALLBACK_SOURCES` list | ✅ |
| 4.4 | Implement `build_prompt()` — return fixed prompt string | ✅ |
| 4.5 | Implement `call_gemini(prompt)` — same pattern as pulse generator | ✅ |
| 4.6 | Implement `parse_response(raw)` — strip fences, parse JSON | ✅ |
| 4.7 | Implement `validate(output)` — check bullet count, validate source domains, replace with fallback if needed, add `last_checked` | ✅ |
| 4.8 | Implement `run()` — chain all functions, print progress, return dict | ✅ |
| 4.9 | Manual test: run standalone and verify output | ✅ |

---

## Phase 5 — Assembler (`src/core/assembler.py`)

| # | Task | Status |
|---|------|--------|
| 5.1 | Implement `assemble(pulse, fee)` — merge into single payload dict with exact schema | ✅ |
| 5.2 | Implement `save(payload)` — write to `outputs/full_payload_YYYY-MM-DD.json` | ✅ |
| 5.3 | Implement `run(pulse, fee)` — assemble + save, print path, return dict | ✅ |

---

## Phase 6 — Approval Gate (`src/core/approval_gate.py`)

| # | Task | Status |
|---|------|--------|
| 6.1 | Implement `display_preview(payload)` — print formatted approval block to terminal | ✅ |
| 6.2 | Implement `prompt_user()` — blocking loop, accept 'a' or 'r' only | ✅ |
| 6.3 | Implement `run(payload)` — display + prompt, print result, return bool | ✅ |

---

## Phase 7 — MCP Actions (`src/mcp/`)

| # | Task | Status |
|---|------|--------|
| 7.1 | `doc_appender.py` — Implement `format_entry(payload)` — build markdown block | ✅ |
| 7.2 | `doc_appender.py` — Implement `append_to_doc(payload)` — call Google Docs MCP endpoint | ✅ |
| 7.3 | `email_drafter.py` — Implement `format_body(payload)` — build email body string | ✅ |
| 7.4 | `email_drafter.py` — Implement `create_draft(payload)` — call Gmail MCP, `create_draft` only, never `send` | ✅ |

---

## Phase 8 — Orchestrator (`main.py`)

| # | Task | Status |
|---|------|--------|
| 8.1 | Implement `main()` with `--ui` flag support (argparse) | ✅ |
| 8.2 | Implement `run_cli()` — existing 5-phase pipeline with CLI approval gate | ✅ |
| 8.3 | Implement `run_with_ui()` — run phases 1–5, then launch Flask dashboard | ✅ |
| 8.4 | Add `log()` helper with timestamps | ✅ |
| 8.5 | End-to-end CLI test: `python main.py` runs full pipeline | ✅ |

---

## Phase 9 — Tests (`tests/`)

| # | Task | Status |
|---|------|--------|
| 9.1 | `test_scraper.py` — test `filter_by_date` drops old reviews | ✅ |
| 9.2 | `test_scraper.py` — test `clean` drops `userName` column | ✅ |
| 9.3 | `test_scraper.py` — test `clean` drops reviews with < 10 words | ✅ |
| 9.4 | `test_scraper.py` — test output CSV has exactly 4 columns | ✅ |
| 9.5 | `test_pulse.py` — test `validate` truncates note to 250 words | ✅ |
| 9.6 | `test_pulse.py` — test `parse_response` strips markdown fences | ✅ |
| 9.7 | `test_pulse.py` — test `validate` raises if top_themes < 3 | ✅ |
| 9.8 | `test_fee.py` — test `validate` replaces sources with fallback for bad domains | ✅ |
| 9.9 | `test_fee.py` — test `validate` raises if bullets > 6 | ✅ |
| 9.10 | `test_fee.py` — test `validate` adds `last_checked` field | ✅ |
| 9.11 | `test_assembler.py` — test `assemble` output contains all required keys | ✅ |
| 9.12 | `test_assembler.py` — test `save` creates file in `outputs/` | ✅ |
| 9.13 | Run full test suite: `pytest tests/` passes | ✅ |

---

## Phase 10 — Web UI Dashboard (`src/ui/`)

| # | Task | Status |
|---|------|--------|
| 10.1 | Create `app.py` — Flask server with routes: `GET /`, `GET /api/payload`, `POST /api/approve`, `POST /api/reject`, `GET /api/status` | ✅ |
| 10.2 | Implement in-memory pipeline state management with threading lock | ✅ |
| 10.3 | `POST /api/approve` accepts `recipients` list from request body, validates emails | ✅ |
| 10.4 | Create `dashboard.html` — single-page template with all card sections | ✅ |
| 10.5 | Create `style.css` — dark-mode glassmorphism design, Inter font, micro-animations | ✅ |
| 10.6 | Create `main.js` — `loadPayload()`, `addRecipient()`, `removeRecipient()`, `handleApprove()`, `handleReject()`, `updateStatus()` | ✅ |
| 10.7 | Recipient email input with chip/pill UI, validation, duplicate prevention | ✅ |
| 10.8 | Approve flow: collect recipients, show confirmation modal, fire MCP, show toast | ✅ |
| 10.9 | Reject flow: disable UI, show toast, update status badge | ✅ |
| 10.10 | End-to-end UI test: `python main.py --ui` → dashboard loads → approve/reject works | ✅ |

---

## Phase 11 — README (`README.md`)

| # | Task | Status |
|---|------|--------|
| 11.1 | Write project overview and features | ✅ |
| 11.2 | Installation and setup instructions | ✅ |
| 11.3 | Usage guide (CLI mode + UI mode) | ✅ |
| 11.4 | Architecture summary and data flow diagram | ✅ |
| 11.5 | Hard constraints section | ✅ |

---

## Hard Constraints Checklist

These must be verified across **every file** before marking any phase complete:

| # | Constraint | Verified |
|---|-----------|----------|
| HC-1 | Package ID is exactly `in.indwealth` | ✅ |
| HC-2 | `userName` dropped before any processing | ✅ |
| HC-3 | Temperature is `0` for both Gemini calls | ✅ |
| HC-4 | Note field ≤ 250 words (truncated in code) | ✅ |
| HC-5 | Fee bullets: 4–6 (validated and raised) | ✅ |
| HC-6 | Source links from approved domains only (fallback if not) | ✅ |
| HC-7 | Approval gate is blocking — no async, no timeout | ✅ |
| HC-8 | Gmail MCP uses `create_draft` only — never `send` | ✅ |
| HC-9 | No API keys in source code — `.env` + `python-dotenv` only | ✅ |
| HC-10 | Never fetch more than 200 reviews | ✅ |
| HC-11 | Only process reviews with actual substantive content | ✅ |

---

## Architecture Document

| # | Task | Status |
|---|------|--------|
| A-1 | Initial architecture draft | ✅ |
| A-2 | Migrate from Claude/Anthropic to Gemini API | ✅ |
| A-3 | Add review quality filtering (no one-word reviews) | ✅ |
| A-4 | Add hard cap of 200 reviews | ✅ |
| A-5 | Add Phase 10 — Web UI Dashboard spec | ✅ |
| A-6 | Add email recipient input to dashboard | ✅ |
| A-7 | Remove actual code from architecture — keep descriptive only | ✅ |
