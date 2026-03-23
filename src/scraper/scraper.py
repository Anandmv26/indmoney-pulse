from google_play_scraper import reviews, Sort
import pandas as pd
from datetime import datetime, timedelta
import os

# --- Constants ---
APP_ID = "in.indwealth"
FETCH_COUNT = 200          # Hard cap — never fetch more than 200 reviews
WEEKS_BACK = 10
MIN_WORD_COUNT = 10         # Reviews with fewer words are dropped as low-quality
OUTPUT_DIR = "data/processed"


def fetch_reviews(count: int) -> list[dict]:
    """
    Fetch reviews from Play Store.
    Enforces hard cap of 200. Drops null, empty, whitespace-only,
    and single-word reviews immediately after fetching.
    """
    count = min(count, 200)  # Hard cap — never request more than 200

    result, _ = reviews(
        APP_ID,
        lang="en",
        country="in",
        sort=Sort.NEWEST,
        count=count,
    )

    # Drop reviews with no content, empty, or whitespace-only
    filtered = []
    for r in result:
        content = r.get("content")
        if content is None:
            continue
        if not isinstance(content, str):
            continue
        stripped = content.strip()
        if not stripped:
            continue
        # Drop single-word reviews (e.g. "good", "nice", "ok", "bad")
        if len(stripped.split()) <= 1:
            continue
        filtered.append(r)

    return filtered


def filter_by_date(reviews_list: list[dict], weeks: int) -> list[dict]:
    """
    Keep only reviews within the last `weeks` weeks.
    """
    cutoff = datetime.now() - timedelta(weeks=weeks)

    filtered = []
    for r in reviews_list:
        review_date = r.get("at")
        if review_date is None:
            continue
        # google_play_scraper returns datetime objects for 'at'
        if isinstance(review_date, datetime):
            if review_date >= cutoff:
                filtered.append(r)
        else:
            # Try to handle if it's a string
            try:
                parsed = datetime.fromisoformat(str(review_date))
                if parsed >= cutoff:
                    filtered.append(r)
            except (ValueError, TypeError):
                continue

    return filtered


def clean(reviews_list: list[dict]) -> pd.DataFrame:
    """
    Convert to DataFrame, drop PII, keep only necessary columns,
    filter low-quality reviews, enforce hard cap of 200 rows.
    """
    df = pd.DataFrame(reviews_list)

    # Drop userName immediately (PII) — no exceptions
    if "userName" in df.columns:
        df = df.drop(columns=["userName"])

    # Keep only required columns
    required_cols = ["at", "score", "content", "thumbsUpCount"]
    existing_cols = [c for c in required_cols if c in df.columns]
    df = df[existing_cols]

    # Rename columns
    rename_map = {
        "at": "date",
        "score": "rating",
        "content": "review_text",
        "thumbsUpCount": "helpful_count",
    }
    df = df.rename(columns=rename_map)

    # Drop rows where review_text is null, empty, or whitespace-only
    if "review_text" in df.columns:
        df = df[df["review_text"].notna()]
        df = df[df["review_text"].astype(str).str.strip().str.len() > 0]

        # Drop rows with fewer than MIN_WORD_COUNT words
        df = df[
            df["review_text"]
            .astype(str)
            .apply(lambda x: len(x.split()) >= MIN_WORD_COUNT)
        ]

    # Sort by date descending and enforce hard cap of 200 rows
    if "date" in df.columns:
        df = df.sort_values("date", ascending=False)
    df = df.head(200)

    # Reset index
    df = df.reset_index(drop=True)

    return df


def save_csv(df: pd.DataFrame) -> str:
    """
    Save the cleaned DataFrame to a CSV file.
    Returns the full file path.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"indmoney_reviews_{datetime.now().strftime('%Y-%m-%d')}.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)
    df.to_csv(filepath, index=False)
    return filepath


def run() -> str:
    """
    Run the full scraper pipeline: fetch → filter → clean → save.
    Returns the CSV file path.
    """
    print("Fetching reviews...")
    raw = fetch_reviews(FETCH_COUNT)

    print("Filtering by date...")
    recent = filter_by_date(raw, WEEKS_BACK)

    print("Cleaning data...")
    df = clean(recent)

    path = save_csv(df)
    print(f"Saved to {path}")

    return path


if __name__ == "__main__":
    csv_path = run()
    print(f"\nDone. Output: {csv_path}")
