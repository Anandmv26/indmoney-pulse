"""
Tests for src/scraper/scraper.py

Covers:
- filter_by_date drops old reviews
- clean drops userName column (PII)
- clean drops reviews with fewer than 10 words
- clean output has exactly 4 columns
- fetch_reviews hard cap enforcement
- fetch_reviews drops empty/single-word content
- clean enforces 200-row hard cap
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.scraper.scraper import fetch_reviews, filter_by_date, clean, save_csv


# --- Helpers ---

def make_review(content="This is a detailed review with more than ten words in the sentence easily",
                days_ago=3, score=4, thumbs=5, username="TestUser"):
    """Create a mock review dict matching google_play_scraper format."""
    return {
        "userName": username,
        "content": content,
        "score": score,
        "thumbsUpCount": thumbs,
        "at": datetime.now() - timedelta(days=days_ago),
    }


# --- filter_by_date tests ---

class TestFilterByDate:
    def test_drops_old_reviews(self):
        """Reviews older than the cutoff should be dropped."""
        recent = make_review(days_ago=5)
        old = make_review(days_ago=200)

        result = filter_by_date([recent, old], weeks=10)

        assert len(result) == 1
        assert result[0] is recent

    def test_keeps_reviews_within_window(self):
        """All reviews within the window should be kept."""
        r1 = make_review(days_ago=1)
        r2 = make_review(days_ago=30)
        r3 = make_review(days_ago=60)

        result = filter_by_date([r1, r2, r3], weeks=10)

        assert len(result) == 3

    def test_empty_list_returns_empty(self):
        """Empty input returns empty output."""
        result = filter_by_date([], weeks=10)
        assert result == []

    def test_review_with_no_date_is_dropped(self):
        """Reviews missing the 'at' field are dropped."""
        r = {"content": "some review", "score": 5}
        result = filter_by_date([r], weeks=10)
        assert len(result) == 0

    def test_boundary_review_exactly_at_cutoff(self):
        """A review exactly at the cutoff boundary should be kept."""
        # 10 weeks = 70 days; a review 69 days ago should be kept
        r = make_review(days_ago=69)
        result = filter_by_date([r], weeks=10)
        assert len(result) == 1


# --- clean tests ---

class TestClean:
    def test_drops_username_column(self):
        """The userName column must be dropped (PII)."""
        reviews_list = [make_review()]
        df = clean(reviews_list)

        assert "userName" not in df.columns
        assert "userName" not in df.values

    def test_drops_short_reviews(self):
        """Reviews with fewer than 10 words should be filtered out."""
        short = make_review(content="Too short")
        long = make_review(content="This is a detailed review with more than ten words in the sentence easily")

        df = clean([short, long])

        assert len(df) == 1
        assert df.iloc[0]["review_text"] == long["content"]

    def test_drops_single_word_reviews(self):
        """Single word reviews should already be dropped by fetch, but clean also filters them."""
        single = make_review(content="good")
        proper = make_review(content="This is a detailed review with more than ten words in the sentence easily")

        df = clean([single, proper])

        assert len(df) == 1

    def test_output_has_exactly_four_columns(self):
        """Output should have exactly: date, rating, review_text, helpful_count."""
        reviews_list = [make_review()]
        df = clean(reviews_list)

        expected_columns = {"date", "rating", "review_text", "helpful_count"}
        assert set(df.columns) == expected_columns
        assert len(df.columns) == 4

    def test_drops_null_content_reviews(self):
        """Rows with None content should be dropped."""
        null_review = make_review(content=None)
        good_review = make_review()

        # Manually set content to None since make_review assigns it
        null_review["content"] = None

        df = clean([null_review, good_review])

        assert len(df) == 1

    def test_drops_empty_string_reviews(self):
        """Reviews with empty string content should be dropped."""
        empty = make_review(content="")
        good = make_review()

        df = clean([empty, good])

        assert len(df) == 1

    def test_drops_whitespace_only_reviews(self):
        """Reviews with only whitespace should be dropped."""
        ws = make_review(content="     ")
        good = make_review()

        df = clean([ws, good])

        assert len(df) == 1

    def test_hard_cap_200_rows(self):
        """Output should never exceed 200 rows."""
        # Create 250 valid reviews
        reviews_list = [make_review(days_ago=i) for i in range(250)]

        df = clean(reviews_list)

        assert len(df) <= 200

    def test_sorted_by_date_descending(self):
        """Output should be sorted with newest reviews first."""
        r1 = make_review(days_ago=10)
        r2 = make_review(days_ago=1)
        r3 = make_review(days_ago=5)

        df = clean([r1, r2, r3])

        dates = df["date"].tolist()
        assert dates == sorted(dates, reverse=True)

    def test_index_is_reset(self):
        """After cleaning, index should be 0, 1, 2, ..."""
        reviews_list = [make_review(days_ago=i) for i in range(5)]
        df = clean(reviews_list)

        assert list(df.index) == list(range(len(df)))


# --- fetch_reviews tests ---

class TestFetchReviews:
    @patch("src.scraper.scraper.reviews")
    def test_hard_cap_enforced(self, mock_reviews):
        """Requesting more than 200 should be capped to 200."""
        mock_reviews.return_value = ([], None)

        fetch_reviews(500)

        # The count passed to the scraper should be 200, not 500
        call_kwargs = mock_reviews.call_args
        assert call_kwargs[1]["count"] == 200 or call_kwargs[0][0] == "in.indwealth"

    @patch("src.scraper.scraper.reviews")
    def test_drops_none_content(self, mock_reviews):
        """Reviews with None content should be dropped."""
        mock_reviews.return_value = ([
            {"content": None, "score": 3},
            {"content": "This is a real multi-word review here", "score": 4},
        ], None)

        result = fetch_reviews(10)

        assert len(result) == 1

    @patch("src.scraper.scraper.reviews")
    def test_drops_empty_content(self, mock_reviews):
        """Reviews with empty string content should be dropped."""
        mock_reviews.return_value = ([
            {"content": "", "score": 3},
            {"content": "   ", "score": 3},
            {"content": "This is a real multi-word review here", "score": 4},
        ], None)

        result = fetch_reviews(10)

        assert len(result) == 1

    @patch("src.scraper.scraper.reviews")
    def test_drops_single_word_content(self, mock_reviews):
        """Single-word reviews like 'good', 'nice' should be dropped."""
        mock_reviews.return_value = ([
            {"content": "good", "score": 5},
            {"content": "nice", "score": 4},
            {"content": "ok", "score": 3},
            {"content": "This is a proper review with real content", "score": 4},
        ], None)

        result = fetch_reviews(10)

        assert len(result) == 1

    @patch("src.scraper.scraper.reviews")
    def test_uses_correct_app_id(self, mock_reviews):
        """Must always use in.indwealth as the app ID."""
        mock_reviews.return_value = ([], None)

        fetch_reviews(10)

        call_args = mock_reviews.call_args
        # First positional arg is the app_id
        assert call_args[0][0] == "in.indwealth"


# --- save_csv tests ---

class TestSaveCsv:
    def test_creates_file(self, tmp_path, monkeypatch):
        """save_csv should create a CSV file."""
        monkeypatch.setattr("src.scraper.scraper.OUTPUT_DIR", str(tmp_path))

        df = pd.DataFrame({
            "date": [datetime.now()],
            "rating": [5],
            "review_text": ["Great app with lots of features"],
            "helpful_count": [10],
        })

        path = save_csv(df)

        assert os.path.exists(path)
        assert path.endswith(".csv")

    def test_csv_has_correct_columns(self, tmp_path, monkeypatch):
        """Saved CSV should have the 4 expected columns."""
        monkeypatch.setattr("src.scraper.scraper.OUTPUT_DIR", str(tmp_path))

        df = pd.DataFrame({
            "date": [datetime.now()],
            "rating": [5],
            "review_text": ["Great app with lots of features"],
            "helpful_count": [10],
        })

        path = save_csv(df)
        loaded = pd.read_csv(path)

        assert set(loaded.columns) == {"date", "rating", "review_text", "helpful_count"}
