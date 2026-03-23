from google import genai
import pandas as pd
import json
import os
import re
from datetime import date
from dotenv import load_dotenv

load_dotenv()

# --- Constants ---
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
MAX_TOKENS = 4000
MAX_NOTE_WORDS = 250

# --- Prompt template ---
PROMPT_TEMPLATE = """You are a product analyst for INDmoney, an Indian personal finance app.

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
{{
  "themes": [
    {{ "name": "string", "description": "string", "review_count": number }}
  ],
  "top_themes": ["string", "string", "string"],
  "quotes": [
    {{ "text": "string", "rating": number }}
  ],
  "note": "string",
  "actions": ["string", "string", "string"]
}}"""


def load_reviews(csv_path: str) -> list[str]:
    """
    Read CSV and return list of review_text strings only.
    """
    df = pd.read_csv(csv_path)
    return df["review_text"].dropna().astype(str).tolist()


def build_prompt(reviews: list[str]) -> str:
    """
    Join reviews with separator and substitute into prompt template.
    """
    review_text_block = "\n---\n".join(reviews)
    return PROMPT_TEMPLATE.format(
        review_count=len(reviews),
        review_text_block=review_text_block,
    )


def call_gemini(prompt: str) -> str:
    """
    Call Gemini API with temperature=0 for deterministic output.
    Returns the raw text response.
    """
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config={"max_output_tokens": MAX_TOKENS, "temperature": 0},
    )
    return response.text


def parse_response(raw: str) -> dict:
    """
    Strip any markdown fences and parse JSON.
    Raises ValueError if parsing fails.
    """
    cleaned = raw.strip()

    # Remove markdown fences if present
    cleaned = re.sub(r"^```json\s*", "", cleaned)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse Gemini response as JSON: {e}\nRaw response:\n{raw}")


def validate(output: dict) -> dict:
    """
    Validate the parsed output against expected schema.
    Truncates note to 250 words if needed.
    Raises ValueError for constraint violations.
    """
    # Check themes count
    if len(output.get("themes", [])) > 5:
        raise ValueError(f"Too many themes: {len(output['themes'])} (max 5)")

    # Check top_themes count
    if len(output.get("top_themes", [])) != 3:
        raise ValueError(f"Expected 3 top_themes, got {len(output.get('top_themes', []))}")

    # Check quotes count
    if len(output.get("quotes", [])) != 3:
        raise ValueError(f"Expected 3 quotes, got {len(output.get('quotes', []))}")

    # Check actions count
    if len(output.get("actions", [])) != 3:
        raise ValueError(f"Expected 3 actions, got {len(output.get('actions', []))}")

    # Truncate note to MAX_NOTE_WORDS if needed
    note = output.get("note", "")
    words = note.split()
    if len(words) > MAX_NOTE_WORDS:
        output["note"] = " ".join(words[:MAX_NOTE_WORDS])

    return output


def run(csv_path: str) -> dict:
    """
    Full pipeline: load_reviews → build_prompt → call_gemini → parse_response → validate.
    Returns validated dict.
    """
    reviews = load_reviews(csv_path)

    prompt = build_prompt(reviews)

    print("Generating weekly pulse...")
    raw = call_gemini(prompt)

    parsed = parse_response(raw)

    result = validate(parsed)
    print("Pulse generated.")

    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m src.pulse.pulse_generator <csv_path>")
        sys.exit(1)
    result = run(sys.argv[1])
    print(json.dumps(result, indent=2, ensure_ascii=False))
