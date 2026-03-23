"""
Approval gate — blocks until the user approves or rejects.
No MCP action fires before this gate passes.
"""


def display_preview(payload: dict) -> None:
    """
    Print a human-readable preview of the payload to the terminal.
    """
    pulse = payload["weekly_pulse"]
    top_themes = pulse["top_themes"]
    actions = pulse["actions"]
    quotes = pulse["quotes"]
    bullets = payload["explanation_bullets"]
    sources = payload["source_links"]

    preview = f"""
============================================================
  INDmoney AI Workflow — Approval Required
============================================================

Date:         {payload["date"]}

TOP 3 THEMES:
  1. {top_themes[0]}
  2. {top_themes[1]}
  3. {top_themes[2]}

WEEKLY NOTE (first 150 chars):
  {pulse["note"][:150]}...

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
"""
    print(preview)


def prompt_user() -> bool:
    """
    Block until user types 'a' (approve) or 'r' (reject).
    Returns True for approve, False for reject.
    """
    while True:
        choice = input("Type 'a' to approve or 'r' to reject: ").strip().lower()
        if choice == "a":
            return True
        elif choice == "r":
            return False
        else:
            print("Invalid input. Please type 'a' or 'r'.")


def run(payload: dict) -> bool:
    """
    Display preview, then prompt for approval.
    Returns True if approved, False if rejected.
    """
    display_preview(payload)
    approved = prompt_user()

    if approved:
        print("Approved. Triggering MCP actions...")
    else:
        print("Rejected. Pipeline exited. No data written.")

    return approved
