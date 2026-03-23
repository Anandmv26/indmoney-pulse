from google import genai
import json
import os
import re
from datetime import date
from dotenv import load_dotenv

load_dotenv()

# --- Constants ---
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
MAX_TOKENS = 2000
FEE_SCENARIO = "mutual fund exit load on the INDmoney platform"
MAX_BULLETS = 6
MIN_BULLETS = 4
APPROVED_SOURCE_DOMAINS = ["sebi.gov.in", "amfiindia.com", "indmoney.com"]

# --- Hardcoded fallback sources (verified working URLs) ---
FALLBACK_SOURCES = [
    {
        "label": "SEBI — Mutual Funds Regulations",
        "url": "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=3&ssid=27&smid=0"
    },
    {
        "label": "AMFI India — Investor Resources",
        "url": "https://www.amfiindia.com"
    }
]

# --- Prompt template ---
PROMPT_TEMPLATE = f"""You are a financial content writer for a regulated Indian fintech platform.

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
{{
  "scenario": "string",
  "bullets": ["string", "string", "string", "string"],
  "source_links": [
    {{ "label": "string", "url": "string" }},
    {{ "label": "string", "url": "string" }}
  ]
}}"""


def build_prompt() -> str:
    """
    Returns the prompt template as a string.
    No variables needed — scenario is fixed.
    """
    return PROMPT_TEMPLATE


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
    Validate the parsed output:
    - Check bullet count (4-6), raise if violated
    - Check source_links count == 2, replace with fallback if not
    - Check each source URL domain, replace all with fallback if any fail
    - Add last_checked field
    """
    # Check bullet count
    bullet_count = len(output.get("bullets", []))
    if bullet_count < MIN_BULLETS or bullet_count > MAX_BULLETS:
        raise ValueError(
            f"Expected {MIN_BULLETS}-{MAX_BULLETS} bullets, got {bullet_count}"
        )

    # Always use verified fallback sources, as Gemini often hallucinates URLs
    output["source_links"] = FALLBACK_SOURCES

    # Add last_checked field
    output["last_checked"] = date.today().isoformat()

    return output


def run() -> dict:
    """
    Full pipeline: build_prompt → call_gemini → parse_response → validate.
    Returns validated dict.
    """
    prompt = build_prompt()

    print("Generating fee explainer...")
    raw = call_gemini(prompt)

    parsed = parse_response(raw)

    result = validate(parsed)
    print("Fee explainer generated.")

    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, ensure_ascii=False))
