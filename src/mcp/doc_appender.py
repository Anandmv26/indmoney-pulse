import os
from dotenv import load_dotenv
from googleapiclient.discovery import build

from src.mcp.auth import get_google_credentials

load_dotenv()


def format_entry(payload: dict) -> str:
    """
    Format the payload into a markdown block for the Google Doc.
    """
    pulse = payload["weekly_pulse"]
    top_themes = ", ".join(pulse["top_themes"])
    note = pulse["note"]
    actions = "\n".join(f"{i+1}. {a}" for i, a in enumerate(pulse["actions"]))
    
    fee_scenario = payload["fee_scenario"]
    bullets = "\n".join(f"• {b}" for b in payload["explanation_bullets"])
    sources = "\n".join(f"- {s['label']}: {s['url']}" for s in payload["source_links"])
    
    return f"""---
Date: {payload["date"]}

Weekly Pulse — Top Themes: {top_themes}

Note:
{note}

Actions:
{actions}

Fee Scenario: {fee_scenario}
Explanation:
{bullets}

Sources:
{sources}

Last checked: {payload["last_checked"]}
---"""


def append_to_doc(payload: dict) -> bool:
    """
    Append formatted payload to Google Doc using the official Google Workspace APIs.
    Returns True on success, False on failure.
    """
    doc_id = os.getenv("TARGET_DOC_ID")
    creds = get_google_credentials()

    if not doc_id:
        print("Doc append failed: Missing TARGET_DOC_ID in environment.")
        return False
    if not creds:
        print("Doc append failed: Invalid or missing GOOGLE_CREDENTIALS_BASE64.")
        return False

    text_to_append = "\n" + format_entry(payload) + "\n"

    try:
        # Build standard Google Docs v1 service
        service = build("docs", "v1", credentials=creds, cache_discovery=False)
        
        # We append text at index 1 (top of document, after title)
        requests = [
            {
                "insertText": {
                    "location": {"index": 1},
                    "text": text_to_append
                }
            }
        ]
        
        # Execute batch update
        service.documents().batchUpdate(
            documentId=doc_id, body={"requests": requests}
        ).execute()

        print("Doc entry appended successfully directly via Google APIs.")
        return True
    
    except Exception as e:
        print(f"Doc append API failed: {e}")
        return False
