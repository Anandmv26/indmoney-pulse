import sys
import argparse
from datetime import datetime

from src.scraper.scraper import run as scrape
from src.pulse.pulse_generator import run as generate_pulse
from src.fee.fee_explainer import run as generate_fee
from src.core.assembler import run as assemble
from src.core.approval_gate import run as approval_gate
from src.mcp.doc_appender import append_to_doc
from src.mcp.email_drafter import create_draft


def log(msg: str) -> None:
    """Print to stdout with a timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def run_pipeline_data() -> dict:
    """Runs the first 4 phases to gather and assemble data."""
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
    
    return payload


def run_cli() -> None:
    """Run the pipeline with the CLI approval gate."""
    payload = run_pipeline_data()

    # Phase 6: CLI Approval gate — BLOCKING
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


def run_with_ui() -> None:
    """Run the pipeline with the Web UI dashboard."""
    payload = run_pipeline_data()
    
    log("Phase 5/5 — Launching Web UI Dashboard...")
    try:
        from src.ui.app import start_ui
        start_ui(payload)
    except ImportError:
        log("ERROR: UI module not found. Please implement Phase 10.")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="INDmoney AI Workflow")
    parser.add_argument(
        "--ui", 
        action="store_true", 
        help="Launch the Web UI Dashboard for approval instead of CLI"
    )
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="Run scraping and AI generation phases only, save payload, and exit (for CI/CD schedules)"
    )
    args = parser.parse_args()

    log("=== INDmoney AI Workflow starting ===")
    
    if args.generate_only:
        run_pipeline_data()
        log("=== Generation complete. Pipeline stopped intentionally. ===")
        sys.exit(0)
    elif args.ui:
        run_with_ui()
    else:
        run_cli()


if __name__ == "__main__":
    main()
