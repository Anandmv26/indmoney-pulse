import json
import os
from datetime import date


def assemble(pulse: dict, fee: dict) -> dict:
    """
    Merge pulse and fee outputs into a single payload dict.
    Returns the exact structure specified in the architecture.
    """
    return {
        "date": date.today().isoformat(),
        "weekly_pulse": {
            "themes": pulse["themes"],
            "top_themes": pulse["top_themes"],
            "quotes": pulse["quotes"],
            "note": pulse["note"],
            "actions": pulse["actions"],
        },
        "fee_scenario": fee["scenario"],
        "explanation_bullets": fee["bullets"],
        "source_links": fee["source_links"],
        "last_checked": fee["last_checked"],
    }


def save(payload: dict) -> str:
    """
    Save payload to outputs/full_payload_YYYY-MM-DD.json.
    Creates the outputs/ directory if it doesn't exist.
    Returns the file path.
    """
    os.makedirs("outputs", exist_ok=True)
    filename = f"full_payload_{payload['date']}.json"
    filepath = os.path.join("outputs", filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return filepath


def run(pulse: dict, fee: dict) -> dict:
    """
    Assemble the payload and save to disk.
    Returns the payload dict.
    """
    payload = assemble(pulse, fee)
    path = save(payload)
    print(f"Payload assembled and saved to {path}")
    return payload


if __name__ == "__main__":
    # Quick test with dummy data
    dummy_pulse = {
        "themes": [{"name": "Test", "description": "Desc", "review_count": 1}],
        "top_themes": ["A", "B", "C"],
        "quotes": [{"text": "q", "rating": 5}],
        "note": "Test note",
        "actions": ["a1", "a2", "a3"],
    }
    dummy_fee = {
        "scenario": "test scenario",
        "bullets": ["b1", "b2", "b3", "b4"],
        "source_links": [{"label": "l", "url": "u"}],
        "last_checked": date.today().isoformat(),
    }
    result = run(dummy_pulse, dummy_fee)
    print(json.dumps(result, indent=2))
