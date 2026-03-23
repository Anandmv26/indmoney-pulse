# INDmoney AI Workflow

An end-to-end automated AI pipeline that scrapes Play Store reviews, analyzes themes, generates fee explainers via the Gemini API, and prepares structural reports via MCP (Model Context Protocol). It supports a **headless CLI execution** and a gorgeous **Web UI Dashboard** for reviewing the report before triggering MCP actions.

[Dashboard Preview]([https://via.placeholder.com/800x450.png?text=Weekly+Pulse+Dashboard+-+Deep+Dark+Visual+Mode](https://indmoney-pulse.onrender.com/))

---

## 🌟 Key Features

1. **Intelligent Play Store Scraping**: Automatically fetches reviews for `in.indwealth`, dropping empty/null datasets, single-word reviews, and scrubs PII (`userName`) instantly. Cap limited to 200 items.
2. **Weekly Product Pulse Generation**: Leverages Google's **Gemini 2.5 Flash** to identify top 3 customer feedback themes, extracts exact quotes, and drafts actionable items. Prompts enforce zero-hallucination guardrails and strict JSON schemas. 
3. **Fee Explainer Generation**: Auto-generates factual, neutral explanation bullets concerning Mutual Fund exit loads, restricting URLs to authorized sources (e.g., *sebi.gov.in*, *amfiindia.com*).
4. **Approval Gate (Dual-Mode)**: The payload stops and requests human approval. You can run the gate solely via the Terminal, or via the Flask-powered Web Dashboard. 
5. **Secure Agentic MCP Routing**: On approval, the pipeline triggers two Model Context Protocol actions safely: 
   - Appending the full markdown digest to a Google Doc.
   - Creating a Gmail Draft (Hard constraint locked to **`create_draft`**—*never auto-sends*).

---

## 🚀 Installation & Setup

**Prerequisites**: Python 3.11+, Git

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd weekly-pulse
   ```

2. **Create a virtual environment and attach dependencies:**
   ```bash
   python -m venv venv
   source venv/Scripts/activate   # Windows
   # source venv/bin/activate     # Mac/Linux
   
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   A template has been provided. Run:
   ```bash
   copy .env.example .env
   ```
   Open `.env` and configure:
   - `GEMINI_API_KEY`: Your working Google Gemini token.
   - `TARGET_DOC_ID`: Google Document ID for the reports to append to.
   - `GDOC_MCP_URL` & `GMAIL_MCP_URL`: URLs for your running MCP action endpoints.
   - `DRAFT_RECIPIENT`: Default fallback recipient for Gmail drafts (Can also be managed dynamically within the Web UI).

---

## 💻 Usage Guide

### 1. Web UI Mode (Recommended)
This launches a standalone Flask server and holds the pipeline payload in memory. Use a desktop browser to beautifully visualize the data, read the quotes, add specific email recipients dynamically, and Approve/Reject.

```bash
python main.py --ui
```
*Navigate to `http://127.0.0.1:5000` to interact with the dashboard.*

### 2. Headless CLI Mode
The pipeline pauses execution natively inside your terminal printing a text-preview format. Perfect for SSH sessions or CI/CD triggering. Type `a` to approve or `r` to reject.

```bash
python main.py
```

---

## 🧠 Architecture Summary & Data Flow

This application is strictly structured to support modular generation, assembly, and testing. It features 127 automated unit tests across 5 main core directories: scraper, pulse, fee, core, and mcp.

```text
Play Store App (in.indwealth)
  ├─► src/scraper.py (Review Caps, Data Cleaning)
        ├─► data/processed/indmoney_reviews_YYYY-MM-DD.csv
              ├─► src/pulse_generator.py (Gemini 2.5 Flash) ──► Pulse Dict
              ├─► src/fee_explainer.py (Gemini 2.5 Flash)   ──► Fee Dict
                    ├─► src/assembler.py
                          ├─► outputs/full_payload_YYYY-MM-DD.json
                                ├─► src/approval_gate.py | OR | src/ui/app.py  ← HUMAN CHECKPOINT
                                      ├─► doc_appender.py  (MCP)
                                      └─► email_drafter.py (MCP)
```

---

## 🛠 Hard Constraints Implemented
This project aligns tightly with critical fintech engineering restrictions:
- All external API calls respect strict maximum output constraints (No loops yielding 500 reviews).
- **Zero API Keys in code**: Keys exclusively sit in un-committed `.env` files.
- **Gmail Restriction**: The HTTP JSON payload dispatched explicitly restricts methods to `create_draft` mitigating any accidental automated mass emails to customers or teams.
- **Pipelined Approvals**: There are no implicit workflow overlaps. The approval gate represents a thread-locking blockade preventing downstream MCP manipulation.
- **Tone Limitations**: Explainer content prohibits qualitative words (e.g. *recommend, suggest, better, worse*) pushing factual, source-linked constraints.
- All sources fallback exclusively to whitelisted regulations boundaries (`sebi.gov.in`, `amfiindia.com`, `indmoney.com`).
