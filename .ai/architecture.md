# INDmoney AI Workflow — Architecture & Build Specification

> **For LLMs / IDEs:** This single file contains everything needed to build the project from scratch.
> Read it fully before generating any code. Build phase by phase in the order listed.

---

## Project summary

An end-to-end automated AI pipeline that:
1. Scrapes INDmoney Google Play Store reviews (package ID: `in.indwealth`)
2. Generates a structured weekly product pulse using Gemini API
3. Generates a fee explainer for mutual fund exit load using Gemini API
4. Gates all actions behind human approval (approval-gated MCP)
5. On approval: appends results to a Google Doc and creates a Gmail draft (no auto-send)

---

## Folder structure

Generate exactly this structure. Do not add or remove any files.

```
indmoney-ai-workflow/
│
├── .ai/
│   └── architecture.md          ← this file
│
├── src/
│   ├── scraper/
│   │   ├── __init__.py
│   │   └── scraper.py           ← Phase 2
│   ├── pulse/
│   │   ├── __init__.py
│   │   └── pulse_generator.py   ← Phase 3
│   ├── fee/
│   │   ├── __init__.py
│   │   └── fee_explainer.py     ← Phase 4
│   ├── core/
│   │   ├── __init__.py
│   │   ├── assembler.py         ← Phase 5
│   │   └── approval_gate.py     ← Phase 6
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── doc_appender.py      ← Phase 7
│   │   └── email_drafter.py     ← Phase 7
│   └── ui/                      ← Phase 10
│       ├── __init__.py
│       ├── app.py
│       ├── static/
│       │   ├── css/
│       │   │   └── style.css
│       │   └── js/
│       │       └── main.js
│       └── templates/
│           └── dashboard.html
│
├── data/
│   ├── raw/                     ← gitignored, scraper raw dump
│   └── processed/               ← gitignored, cleaned CSVs
│
├── outputs/                     ← gitignored, all generated files
│
├── tests/
│   ├── test_scraper.py
│   ├── test_pulse.py
│   ├── test_fee.py
│   └── test_assembler.py
│
├── main.py                      ← Phase 8, single entry point
├── requirements.txt             ← Phase 1
├── .env.example                 ← Phase 1
├── .env                         ← gitignored, never commit
├── .gitignore                   ← Phase 1
└── README.md                    ← Phase 9
```

---

## Phase 1 — Project setup

### `requirements.txt`
```
google-play-scraper
google-genai
python-dotenv
pandas
flask
```

### `.env.example`
```
GEMINI_API_KEY=your_gemini_api_key_here
GMAIL_MCP_URL=
GDOC_MCP_URL=
TARGET_DOC_ID=your_google_doc_id_here
DRAFT_RECIPIENT=
```

### `.gitignore`
```
.env
venv/
__pycache__/
*.pyc
data/raw/
data/processed/
outputs/
.DS_Store
```

---

## Phase 2 — Scraper (`src/scraper/scraper.py`)

### Purpose
Fetch INDmoney Play Store reviews, clean them, remove PII, save as CSV.

### Dependencies
```python
from google_play_scraper import reviews, Sort
import pandas as pd
from datetime import datetime, timedelta
import os
```

### Constants
```python
APP_ID = "in.indwealth"
FETCH_COUNT = 200          # Hard cap — never fetch more than 200 reviews
WEEKS_BACK = 10
MIN_WORD_COUNT = 10         # Reviews with fewer words are dropped as low-quality
OUTPUT_DIR = "data/processed"
```

### Functions to implement

**`fetch_reviews(count: int) -> list[dict]`**
- Enforce hard cap: `count = min(count, 200)` — never request more than 200
- Call `google_play_scraper.reviews()` with:
  - `app_id = "in.indwealth"`
  - `lang = "en"`
  - `country = "in"`
  - `sort = Sort.NEWEST`
  - `count = count`
- After fetching, immediately drop reviews where `content` is `None`, empty string, or whitespace-only
- Drop reviews where `content` is a single word (e.g. "good", "nice", "ok", "bad")
- Returns the filtered list of review dicts (guaranteed to contain only reviews with actual multi-word content)

**`filter_by_date(reviews: list[dict], weeks: int) -> list[dict]`**
- Calculate cutoff = today minus `weeks * 7` days
- Keep only reviews where `review["at"] >= cutoff`
- Returns filtered list

**`clean(reviews: list[dict]) -> pd.DataFrame`**
- Convert to DataFrame
- Drop column `userName` immediately (PII)
- Keep only columns: `at`, `score`, `content`, `thumbsUpCount`
- Rename columns to: `date`, `rating`, `review_text`, `helpful_count`
- Drop rows where `review_text` is null, empty, or whitespace-only
- Drop rows where `len(review_text.split()) < MIN_WORD_COUNT` (removes one-word, two-word, and other low-quality reviews)
- After all filters, enforce hard cap: keep only the first 200 rows (sorted by date descending)
- Reset index
- Returns cleaned DataFrame

**`save_csv(df: pd.DataFrame) -> str`**
- Filename: `indmoney_reviews_YYYY-MM-DD.csv` using today's date
- Save to `data/processed/`
- Create directory if it doesn't exist
- Returns the full file path as a string

**`run() -> str`**
- Calls all four functions in sequence: fetch → filter → clean → save
- Prints progress at each step: "Fetching reviews...", "Filtering by date...", "Cleaning data...", "Saved to {path}"
- Returns the CSV file path for use by the next phase

---

## Phase 3 — Pulse generator (`src/pulse/pulse_generator.py`)

### Purpose
Read the cleaned CSV and call Gemini API to produce a structured weekly product pulse.

### Dependencies
```python
import google.generativeai as genai
import pandas as pd
import json
import os
from datetime import date
from dotenv import load_dotenv
load_dotenv()
```

### Constants
```python
MODEL = "gemini-2.5-flash"
MAX_TOKENS = 1500
MAX_NOTE_WORDS = 250
```

### Prompt template
Use this exact prompt. Do not modify the structure.

```
You are a product analyst for INDmoney, an Indian personal finance app.

Below are {review_count} user reviews from the Google Play Store, collected over the last 10 weeks.

REVIEWS:
{review_text_block}

Your task:
1. Group these reviews into a maximum of 5 distinct themes. A theme is a recurring topic or issue.
2. Identify the top 3 themes by frequency and importance.
3. Extract exactly 3 verbatim quotes from the reviews above. Copy word-for-word. Do not paraphrase.
4. Write a weekly product pulse note of no more than 250 words for a product manager audience.
5. Propose exactly 3 concrete action ideas for the product or support team.

Hard rules:
- No reviewer names or personal information anywhere in the output.
- Do not invent themes not present in the reviews.
- Note field must be 250 words or fewer.
- Quotes must be copied verbatim from the review text provided.

Return ONLY valid JSON. No markdown fences, no explanation, no preamble.

JSON schema:
{
  "themes": [
    { "name": "string", "description": "string", "review_count": number }
  ],
  "top_themes": ["string", "string", "string"],
  "quotes": [
    { "text": "string", "rating": number }
  ],
  "note": "string",
  "actions": ["string", "string", "string"]
}
```

### Functions to implement

**`load_reviews(csv_path: str) -> list[str]`**
- Read CSV from `csv_path`
- Return list of strings from the `review_text` column only

**`build_prompt(reviews: list[str]) -> str`**
- Join all review strings with `\n---\n` separator
- Substitute `{review_count}` and `{review_text_block}` in the prompt template above
- Returns the complete prompt string

**`call_gemini(prompt: str) -> str`**
- Instantiate `genai.Client(api_key=os.getenv("GEMINI_API_KEY"))`
- Call `client.models.generate_content()` with:
  - `model = MODEL`
  - `contents = prompt`
  - `config = {"max_output_tokens": MAX_TOKENS, "temperature": 0}`
- Returns `response.text`

**`parse_response(raw: str) -> dict`**
- Strip any markdown fences: remove ` ```json ` and ` ``` ` if present
- Parse with `json.loads()`
- Raise `ValueError` with a clear message if parsing fails

**`validate(output: dict) -> dict`**
- Check `len(output["themes"]) <= 5` — raise if violated
- Check `len(output["top_themes"]) == 3` — raise if violated
- Check `len(output["quotes"]) == 3` — raise if violated
- Check `len(output["actions"]) == 3` — raise if violated
- Count words in `output["note"]` — if over 250, truncate to 250 words and rejoin
- Returns the validated (and possibly truncated) dict

**`run(csv_path: str) -> dict`**
- Chains: load_reviews → build_prompt → call_gemini → parse_response → validate
- Prints: "Generating weekly pulse..." before API call
- Prints: "Pulse generated." on success
- Returns validated dict

---

## Phase 4 — Fee explainer (`src/fee/fee_explainer.py`)

### Purpose
Call Gemini API to generate a structured, neutral, factual explanation of mutual fund exit load.

### Dependencies
```python
import google.generativeai as genai
import json
import os
from datetime import date
from dotenv import load_dotenv
load_dotenv()
```

### Constants
```python
MODEL = "gemini-2.5-flash"
MAX_TOKENS = 800
FEE_SCENARIO = "mutual fund exit load on the INDmoney platform"
MAX_BULLETS = 6
MIN_BULLETS = 4
```

### Prompt template
Use this exact prompt.

```
You are a financial content writer for a regulated Indian fintech platform.

Write a factual explanation of the following fee scenario:
{FEE_SCENARIO}

Rules:
- Write between 4 and 6 bullet points. Each bullet is a complete factual statement.
- Tone must be strictly neutral and factual only.
- Forbidden words: recommend, suggest, avoid, best, worst, better, worse, should, must, always, never.
- Do not compare this fee to fees on any other platform or app.
- Do not provide investment advice of any kind.
- Provide exactly 2 official source links. Sources must be from these domains only:
  sebi.gov.in, amfiindia.com, or indmoney.com/help

Return ONLY valid JSON. No markdown, no explanation, no preamble.

JSON schema:
{
  "scenario": "string",
  "bullets": ["string", "string", "string", "string"],
  "source_links": [
    { "label": "string", "url": "string" },
    { "label": "string", "url": "string" }
  ]
}
```

### Hardcoded fallback sources (use if Gemini returns non-approved domains)
```python
FALLBACK_SOURCES = [
    {
        "label": "SEBI Mutual Fund Regulations",
        "url": "https://www.sebi.gov.in/legal/regulations/aug-1996/sebi-mutual-fund-regulations-1996_11603.html"
    },
    {
        "label": "AMFI — Exit Load explained",
        "url": "https://www.amfiindia.com/investor-corner/knowledge-center/exit-load.html"
    }
]
```

### Functions to implement

**`build_prompt() -> str`**
- Returns the prompt template above as a string (no variables needed, scenario is fixed)

**`call_gemini(prompt: str) -> str`**
- Same pattern as pulse_generator — instantiate client, call with `temperature=0`, return text

**`parse_response(raw: str) -> dict`**
- Strip markdown fences, parse JSON, raise `ValueError` on failure

**`validate(output: dict) -> dict`**
- Check `MIN_BULLETS <= len(output["bullets"]) <= MAX_BULLETS` — raise if violated
- Check `len(output["source_links"]) == 2` — if not, replace with `FALLBACK_SOURCES`
- For each source_link URL, check that it contains one of `APPROVED_SOURCE_DOMAINS`
- If any URL fails domain check, replace entire source_links with `FALLBACK_SOURCES`
- Add field `"last_checked": date.today().isoformat()` to the output dict
- Returns validated dict

**`run() -> dict`**
- Chains: build_prompt → call_gemini → parse_response → validate
- Prints: "Generating fee explainer..." before API call
- Prints: "Fee explainer generated." on success
- Returns validated dict

---

## Phase 5 — Assembler (`src/core/assembler.py`)

### Purpose
Merge pulse and fee outputs into one payload. Save to disk.

### Functions to implement

**`assemble(pulse: dict, fee: dict) -> dict`**
- Returns this exact structure:
```python
{
    "date": date.today().isoformat(),
    "weekly_pulse": {
        "themes": pulse["themes"],
        "top_themes": pulse["top_themes"],
        "quotes": pulse["quotes"],
        "note": pulse["note"],
        "actions": pulse["actions"]
    },
    "fee_scenario": fee["scenario"],
    "explanation_bullets": fee["bullets"],
    "source_links": fee["source_links"],
    "last_checked": fee["last_checked"]
}
```

**`save(payload: dict) -> str`**
- Filename: `outputs/full_payload_YYYY-MM-DD.json`
- Create `outputs/` directory if it doesn't exist
- Write with `json.dumps(payload, indent=2, ensure_ascii=False)`
- Returns file path

**`run(pulse: dict, fee: dict) -> dict`**
- Calls assemble, then save
- Prints: "Payload assembled and saved to {path}"
- Returns the payload dict

---

## Phase 6 — Approval gate (`src/core/approval_gate.py`)

### Purpose
Show a human-readable preview. Block until the user approves or rejects. No MCP action fires before this.

### Functions to implement

**`display_preview(payload: dict) -> None`**
- Print the following formatted block to terminal:

```
============================================================
  INDmoney AI Workflow — Approval Required
============================================================

Date:         {payload["date"]}

TOP 3 THEMES:
  1. {top_themes[0]}
  2. {top_themes[1]}
  3. {top_themes[2]}

WEEKLY NOTE (first 150 chars):
  {payload["weekly_pulse"]["note"][:150]}...

FEE SCENARIO:  {payload["fee_scenario"]}
BULLETS:       {len(bullets)} items ready
SOURCES:       {len(sources)} links

ACTION IDEAS:
  1. {actions[0]}
  2. {actions[1]}
  3. {actions[2]}

USER QUOTES:
  - "{quotes[0]["text"][:80]}..."
  - "{quotes[1]["text"][:80]}..."
  - "{quotes[2]["text"][:80]}..."

------------------------------------------------------------
  MCP actions pending:
    [1] Append structured entry to Google Doc
    [2] Create Gmail draft (no auto-send)
------------------------------------------------------------
```

**`prompt_user() -> bool`**
- Loop until valid input:
  ```python
  while True:
      choice = input("Type 'a' to approve or 'r' to reject: ").strip().lower()
      if choice == 'a':
          return True
      elif choice == 'r':
          return False
      else:
          print("Invalid input. Please type 'a' or 'r'.")
  ```

**`run(payload: dict) -> bool`**
- Calls display_preview, then prompt_user
- If approved: prints "Approved. Triggering MCP actions..." and returns True
- If rejected: prints "Rejected. Pipeline exited. No data written." and returns False

---

## Phase 7 — MCP actions (`src/mcp/`)

### `doc_appender.py`

#### Purpose
Append the structured payload as a readable entry in a Google Doc via MCP.

#### Dependencies
```python
import requests
import json
import os
from dotenv import load_dotenv
load_dotenv()
```

#### Format the payload before appending
Convert to this markdown block:

```
---
Date: {date}

Weekly Pulse — Top Themes: {theme1}, {theme2}, {theme3}

Note:
{full note text}

Actions:
1. {action1}
2. {action2}
3. {action3}

Fee Scenario: {fee_scenario}
Explanation:
• {bullet1}
• {bullet2}
• {bullet3}
• {bullet4}

Sources:
- {label1}: {url1}
- {label2}: {url2}

Last checked: {last_checked}
---
```

#### Functions to implement

**`format_entry(payload: dict) -> str`**
- Builds the markdown block above from the payload dict
- Returns formatted string

**`append_to_doc(payload: dict) -> bool`**
- Get `TARGET_DOC_ID` and `GDOC_MCP_URL` from environment
- Call the Google Docs MCP endpoint to append `format_entry(payload)` to the document
- Wrap entire call in try/except
- On success: print "Doc entry appended successfully." and return True
- On failure: print "Doc append failed: {error}" and return False

---

### `email_drafter.py`

#### Purpose
Create a Gmail draft containing the full pulse and fee explainer. Never send.

#### Email body template
```
Subject: Weekly Pulse + Fee Explainer — {date}

Hi team,

== WEEKLY PRODUCT PULSE — {date} ==

{full note text}

Top themes: {theme1} | {theme2} | {theme3}

Action ideas:
1. {action1}
2. {action2}
3. {action3}

User quotes:
- "{quote1_text}"
- "{quote2_text}"
- "{quote3_text}"


== FEE EXPLAINER — {fee_scenario} ==

• {bullet1}
• {bullet2}
• {bullet3}
• {bullet4}

Official sources:
- {source_label1}: {source_url1}
- {source_label2}: {source_url2}

Last checked: {last_checked}

---
Generated by INDmoney AI Workflow. This is a draft — review before sending.
```

#### Functions to implement

**`format_body(payload: dict) -> str`**
- Builds the email body string above from the payload dict
- Returns the formatted string

**`create_draft(payload: dict) -> bool`**
- Get `GMAIL_MCP_URL` and `DRAFT_RECIPIENT` from environment
- Build subject: `f"Weekly Pulse + Fee Explainer — {payload['date']}"`
- Call the Gmail MCP endpoint to create a draft with the subject and body
- Must use `create_draft` method — never `send` or `send_message`
- Wrap entire call in try/except
- On success: print "Gmail draft created successfully. Check your Drafts folder." and return True
- On failure: print "Gmail draft failed: {error}" and return False

---

## Phase 8 — Orchestrator (`main.py`)

### Purpose
Single entry point. Runs all phases in order. Handles the approval gate. Calls MCP only after approval.

### Full implementation

```python
import sys
from datetime import datetime
from src.scraper.scraper import run as scrape
from src.pulse.pulse_generator import run as generate_pulse
from src.fee.fee_explainer import run as generate_fee
from src.core.assembler import run as assemble
from src.core.approval_gate import run as approval_gate
from src.mcp.doc_appender import append_to_doc
from src.mcp.email_drafter import create_draft

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def main():
    log("=== INDmoney AI Workflow starting ===")

    # Phase 2: Scrape
    log("Phase 1/5 — Scraping Play Store reviews...")
    csv_path = scrape()

    # Phase 3: Generate pulse
    log("Phase 2/5 — Generating weekly pulse...")
    pulse = generate_pulse(csv_path)

    # Phase 4: Generate fee explainer
    log("Phase 3/5 — Generating fee explainer...")
    fee = generate_fee()

    # Phase 5: Assemble payload
    log("Phase 4/5 — Assembling payload...")
    payload = assemble(pulse, fee)

    # Phase 6: Approval gate — BLOCKING
    log("Phase 5/5 — Awaiting human approval...")
    approved = approval_gate(payload)

    if not approved:
        log("Pipeline exited by user. No MCP actions taken.")
        sys.exit(0)

    # Phase 7: MCP actions (only if approved)
    log("Triggering MCP actions...")
    doc_ok = append_to_doc(payload)
    email_ok = create_draft(payload)

    # Summary
    log("=== Pipeline complete ===")
    log(f"  Doc append:    {'OK' if doc_ok else 'FAILED'}")
    log(f"  Gmail draft:   {'OK' if email_ok else 'FAILED'}")

if __name__ == "__main__":
    main()
```

---

## Phase 9 — Tests (`tests/`)

### `tests/test_scraper.py`
- Test that `filter_by_date` correctly drops reviews older than cutoff
- Test that `clean` drops the `userName` column
- Test that `clean` drops reviews with fewer than 10 words
- Test that output CSV has exactly 4 columns: `date, rating, review_text, helpful_count`

### `tests/test_pulse.py`
- Test that `validate` truncates note to 250 words if longer
- Test that `parse_response` strips markdown fences before parsing
- Test that `validate` raises if top_themes has fewer than 3 items

### `tests/test_fee.py`
- Test that `validate` replaces sources with fallback if domain not in approved list
- Test that `validate` raises if bullets exceed 6
- Test that `validate` adds `last_checked` field

### `tests/test_assembler.py`
- Test that `assemble` output contains all required keys
- Test that `save` creates the file in the `outputs/` directory

---

## Hard constraints — enforce in every file

1. Package ID is exactly `in.indwealth` — nowhere else
2. Drop `userName` before any other processing step — no exceptions
3. Temperature is always `0` for both Gemini calls — deterministic output
4. Note field must never exceed 250 words — truncate in code, do not rely on the model
5. Fee bullets: minimum 4, maximum 6 — validate and raise if violated
6. Source links must be from `sebi.gov.in`, `amfiindia.com`, or `indmoney.com` — replace with fallback otherwise
7. Approval gate must be a blocking call — no async, no timeout, no skip
8. Gmail MCP must use `create_draft` only — never call `send` under any condition
9. No API keys in source code — read from `.env` via `python-dotenv` only
10. Never fetch more than 200 reviews — enforce cap in both `fetch_reviews` and `clean`
11. Only process reviews with actual substantive content — drop null, empty, whitespace-only, and single-word reviews before any analysis, do not rely on the model

---

## Data flow summary

```
Play Store (in.indwealth)
  └─► scraper.py
        └─► data/processed/indmoney_reviews_YYYY-MM-DD.csv
              ├─► pulse_generator.py ──► pulse dict
              └─► fee_explainer.py   ──► fee dict
                    └─► assembler.py
                          └─► outputs/full_payload_YYYY-MM-DD.json
                                └─► approval_gate.py  ← HUMAN CHECKPOINT
                                      ├─► doc_appender.py  (MCP)
                                      └─► email_drafter.py (MCP)
```

---

## How to run

```bash
# Install
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Fill in ANTHROPIC_API_KEY, TARGET_DOC_ID, DRAFT_RECIPIENT

# Run
python main.py
```

One command. The pipeline runs fully automated until the approval gate, where it pauses for human input. Type `a` to approve and trigger MCP actions. Type `r` to exit cleanly.

---

## Phase 10 — Web UI Dashboard (`src/ui/`)

### Purpose
Provide a modern, visually stunning web interface that replaces the CLI-only approval flow. The dashboard displays the full pipeline output (pulse, fee explainer, themes, quotes, actions), lets the user enter email recipients, and gates MCP actions behind on-screen approve/reject buttons.

### Folder structure addition
```
src/
└── ui/
    ├── __init__.py
    ├── app.py                ← Flask server + API routes
    ├── static/
    │   ├── css/
    │   │   └── style.css     ← Dark-mode glassmorphism design
    │   └── js/
    │       └── main.js       ← Frontend interactivity
    └── templates/
        └── dashboard.html    ← Single-page dashboard template
```

### Dependencies (add to `requirements.txt`)
```
flask
```

### Design spec
- **Dark mode** with a deep navy/charcoal background (`#0f0f1a`)
- **Glassmorphism cards** — frosted-glass effect using `backdrop-filter: blur`, semi-transparent card backgrounds, subtle glass borders
- **Accent color palette**: Electric indigo → Violet → Cyan for highlights, green for approve, red for reject
- **Typography**: Google Font `Inter` (weights: 400, 500, 600, 700)
- **Micro-animations**: cards fade-in-up on load with staggered delays, buttons lift and glow on hover, status badge pulses gently
- **Responsive**: desktop-first layout, gracefully stacks to single column on tablet

### Dashboard layout (`dashboard.html`)

```
┌──────────────────────────────────────────────────────────┐
│  ░ INDmoney AI Workflow              Status: ● Ready     │
│  ░ Weekly Pulse Dashboard            Date: 2026-03-22    │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────────┐  ┌────────────────────────────┐ │
│  │  📊 TOP THEMES      │  │  📝 WEEKLY NOTE            │ │
│  │                     │  │                            │ │
│  │  1. Theme name      │  │  Full note text rendered   │ │
│  │     12 reviews      │  │  with nice typography      │ │
│  │  2. Theme name      │  │                            │ │
│  │     8 reviews       │  │                            │ │
│  │  3. Theme name      │  │                            │ │
│  │     5 reviews       │  │                            │ │
│  └─────────────────────┘  └────────────────────────────┘ │
│                                                          │
│  ┌─────────────────────┐  ┌────────────────────────────┐ │
│  │  💬 USER QUOTES     │  │  🚀 ACTION IDEAS           │ │
│  │                     │  │                            │ │
│  │  "Quote 1..."  ★4   │  │  1. Action item            │ │
│  │  "Quote 2..."  ★2   │  │  2. Action item            │ │
│  │  "Quote 3..."  ★5   │  │  3. Action item            │ │
│  └─────────────────────┘  └────────────────────────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  💰 FEE EXPLAINER — Mutual Fund Exit Load           │ │
│  │                                                      │ │
│  │  • Bullet 1                                          │ │
│  │  • Bullet 2                                          │ │
│  │  • Bullet 3                                          │ │
│  │  • Bullet 4                                          │ │
│  │                                                      │ │
│  │  Sources: SEBI | AMFI                   Last: today  │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  ✉️  RECIPIENTS                                      │ │
│  │                                                      │ │
│  │  ┌──────────────────────────────────────┐  ┌──────┐ │ │
│  │  │  Enter email address...              │  │ + Add│ │ │
│  │  └──────────────────────────────────────┘  └──────┘ │ │
│  │                                                      │ │
│  │  ┌────────────────────────────┐                      │ │
│  │  │ pm@company.com           ✕ │                      │ │
│  │  │ lead@company.com         ✕ │                      │ │
│  │  └────────────────────────────┘                      │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────────┐ │
│  │         ┌────────────┐    ┌────────────┐            │ │
│  │         │ ✓ APPROVE  │    │ ✗ REJECT   │            │ │
│  │         └────────────┘    └────────────┘            │ │
│  │                                                      │ │
│  │  MCP actions pending:                                │ │
│  │    [1] Append to Google Doc                          │ │
│  │    [2] Create Gmail draft → recipients listed above  │ │
│  └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### Backend — `app.py`

#### Flask routes

**`GET /`** — Serve the dashboard
- If payload exists in memory → render `dashboard.html` with data
- If no payload yet → render a "Pipeline not yet run" splash screen

**`GET /api/payload`** — Return the current payload as JSON
- Returns `{"status": "ready", "payload": {...}}` if pipeline has run
- Returns `{"status": "pending"}` if not yet run

**`POST /api/approve`** — Approve the payload
- Accepts JSON body with a `recipients` field — a list of email addresses entered by the user on the dashboard
- Validate that `recipients` is a non-empty list of valid email strings before proceeding
- Triggers MCP actions (doc append + email draft), passing the recipients list to the email drafter
- Returns `{"status": "approved", "doc_ok": true/false, "email_ok": true/false}`
- Sets internal state to prevent double-approval

**`POST /api/reject`** — Reject the payload
- Sets status to rejected, no MCP actions fire
- Returns `{"status": "rejected"}`

**`GET /api/status`** — Return pipeline status
- One of: `pending`, `ready`, `approved`, `rejected`

#### State management
- Use a simple in-memory dict to hold the payload, status, and MCP results
- Protect with a threading lock for thread safety
- Track: `status` (pending | ready | approved | rejected), `payload` (the assembled dict), `results` (MCP outcomes after approval)

### Frontend — `style.css`

#### Visual language
- **Background**: deep navy/charcoal base color
- **Cards**: frosted-glass effect with semi-transparent backgrounds, subtle glass borders, gentle lift and glow on hover
- **Buttons**: gradient backgrounds (green for approve, red for reject), lift on hover with glowing box-shadow
- **Inputs**: the email input field should match the glassmorphism card style — transparent background, glass border, light placeholder text, focus state with accent border glow
- **Recipient chips**: each added email renders as a removable pill/chip with a small ✕ button, styled with semi-transparent accent background
- **Animations**: all cards fade-in-up on page load with staggered delays (0.1s apart), buttons transition smoothly on hover, status badge has a gentle pulse animation
- **Typography**: use `Inter` from Google Fonts throughout, with appropriate weight hierarchy (700 for headings, 600 for labels, 400 for body)

### Frontend — `main.js`

#### Key functions

**`loadPayload()`**
- Fetch `GET /api/payload`
- If status is `ready`, populate all dashboard cards with data
- If status is `pending`, show a loading spinner

**`addRecipient()`**
- Read the email input field value
- Validate it as a proper email format (basic regex check)
- If valid, add it as a chip/pill to the recipients list and clear the input
- If invalid, show a brief inline error message
- Prevent duplicate emails from being added

**`removeRecipient(email)`**
- Remove the specified email chip from the recipients list

**`handleApprove()`**
- Collect all emails from the recipients list
- If no recipients added, show a warning: "Add at least one recipient before approving"
- Show confirmation modal: "This will append to Google Doc and create a Gmail draft to [recipients]. Proceed?"
- On confirm: `POST /api/approve` with `{"recipients": [...]}`
- Show success/failure toast notification
- Disable both buttons and the recipient input after action
- Update status badge to "Approved ✓"

**`handleReject()`**
- `POST /api/reject`
- Show rejection toast
- Disable both buttons and the recipient input
- Update status badge to "Rejected ✗"

**`updateStatus()`**
- Poll `GET /api/status` every 3 seconds while status is `pending`
- Auto-refresh dashboard when status changes to `ready`

### Integration with `main.py`

Update `main.py` to support two modes via a `--ui` command-line flag:

- If `--ui` is passed → run the web dashboard flow (`run_with_ui`)
- If no flag → run the existing CLI flow (`run_cli`)

**`run_with_ui()` flow**:
1. Run phases 1–5 (scrape → pulse → fee → assemble)
2. Load the assembled payload into the in-memory pipeline state
3. Set status to `ready`
4. Start the Flask dev server on `http://localhost:5000`
5. Print: "Dashboard ready at http://localhost:5000 — open in browser to review and approve."
6. Flask handles approval/rejection via the UI buttons
7. On approve: the `/api/approve` route handler triggers MCP actions, passing the user-entered recipients to the email drafter

### Updated run command
```bash
# CLI mode (original)
python main.py

# Web UI mode
python main.py --ui
```
