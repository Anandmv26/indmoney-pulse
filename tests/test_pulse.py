"""
Tests for src/pulse/pulse_generator.py

Covers:
- load_reviews reads CSV and returns list of strings
- build_prompt substitutes review count and text block
- parse_response strips markdown fences before parsing
- parse_response raises ValueError on invalid JSON
- validate truncates note to 250 words if longer
- validate raises if top_themes count != 3
- validate raises if quotes count != 3
- validate raises if actions count != 3
- validate raises if themes count > 5
- validate passes valid output unchanged
"""

import pytest
import pandas as pd
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.pulse.pulse_generator import (
    load_reviews,
    build_prompt,
    parse_response,
    validate,
)


# --- Helpers ---

def make_valid_output(**overrides):
    """Create a valid pulse output dict for testing."""
    base = {
        "themes": [
            {"name": "Performance", "description": "App speed issues", "review_count": 15},
            {"name": "UX", "description": "User experience", "review_count": 10},
            {"name": "Support", "description": "Customer support", "review_count": 8},
        ],
        "top_themes": ["Performance", "UX", "Support"],
        "quotes": [
            {"text": "The app crashes every time I open it", "rating": 1},
            {"text": "Love the redesigned dashboard interface", "rating": 5},
            {"text": "Support team took 3 days to respond", "rating": 2},
        ],
        "note": "This week saw significant user feedback around performance issues.",
        "actions": [
            "Investigate crash reports on Android 14",
            "Add live chat support option",
            "Optimize dashboard load time",
        ],
    }
    base.update(overrides)
    return base


# --- load_reviews tests ---

class TestLoadReviews:
    def test_reads_review_text_column(self, tmp_path):
        """Should return list of strings from review_text column."""
        csv_path = tmp_path / "reviews.csv"
        df = pd.DataFrame({
            "date": ["2026-03-01", "2026-03-02"],
            "rating": [4, 5],
            "review_text": ["Great app for investing", "Best finance app ever"],
            "helpful_count": [3, 7],
        })
        df.to_csv(csv_path, index=False)

        result = load_reviews(str(csv_path))

        assert len(result) == 2
        assert result[0] == "Great app for investing"
        assert result[1] == "Best finance app ever"

    def test_drops_nan_values(self, tmp_path):
        """NaN review_text values should be dropped."""
        csv_path = tmp_path / "reviews.csv"
        df = pd.DataFrame({
            "date": ["2026-03-01", "2026-03-02", "2026-03-03"],
            "rating": [4, 5, 3],
            "review_text": ["Valid review here", None, "Another valid review"],
            "helpful_count": [3, 7, 1],
        })
        df.to_csv(csv_path, index=False)

        result = load_reviews(str(csv_path))

        assert len(result) == 2

    def test_returns_strings(self, tmp_path):
        """All returned items should be strings."""
        csv_path = tmp_path / "reviews.csv"
        df = pd.DataFrame({
            "date": ["2026-03-01"],
            "rating": [4],
            "review_text": ["Test review"],
            "helpful_count": [3],
        })
        df.to_csv(csv_path, index=False)

        result = load_reviews(str(csv_path))

        assert all(isinstance(r, str) for r in result)


# --- build_prompt tests ---

class TestBuildPrompt:
    def test_substitutes_review_count(self):
        """Prompt should contain the correct review count."""
        reviews = ["Review one text", "Review two text"]
        prompt = build_prompt(reviews)

        assert "2 user reviews" in prompt

    def test_substitutes_review_text(self):
        """Prompt should contain the actual review text."""
        reviews = ["This app is amazing for tracking investments"]
        prompt = build_prompt(reviews)

        assert "This app is amazing for tracking investments" in prompt

    def test_joins_with_separator(self):
        """Reviews should be joined with --- separator."""
        reviews = ["Review A", "Review B"]
        prompt = build_prompt(reviews)

        assert "Review A\n---\nReview B" in prompt

    def test_contains_json_schema(self):
        """Prompt should include the expected JSON schema."""
        prompt = build_prompt(["Some review"])

        assert '"themes"' in prompt
        assert '"top_themes"' in prompt
        assert '"quotes"' in prompt
        assert '"note"' in prompt
        assert '"actions"' in prompt


# --- parse_response tests ---

class TestParseResponse:
    def test_parses_clean_json(self):
        """Should parse valid JSON without fences."""
        raw = json.dumps(make_valid_output())
        result = parse_response(raw)

        assert result["top_themes"] == ["Performance", "UX", "Support"]

    def test_strips_json_markdown_fence(self):
        """Should strip ```json ... ``` fences before parsing."""
        inner = json.dumps(make_valid_output())
        raw = f"```json\n{inner}\n```"

        result = parse_response(raw)

        assert "themes" in result
        assert len(result["themes"]) == 3

    def test_strips_plain_markdown_fence(self):
        """Should strip ``` ... ``` fences (without json label)."""
        inner = json.dumps(make_valid_output())
        raw = f"```\n{inner}\n```"

        result = parse_response(raw)

        assert "themes" in result

    def test_raises_on_invalid_json(self):
        """Should raise ValueError for unparseable content."""
        with pytest.raises(ValueError, match="Failed to parse"):
            parse_response("This is not JSON at all")

    def test_raises_on_partial_json(self):
        """Should raise ValueError for incomplete JSON."""
        with pytest.raises(ValueError, match="Failed to parse"):
            parse_response('{"themes": [')

    def test_handles_whitespace_around_json(self):
        """Should handle leading/trailing whitespace."""
        inner = json.dumps(make_valid_output())
        raw = f"\n\n  {inner}  \n\n"

        result = parse_response(raw)

        assert "themes" in result


# --- validate tests ---

class TestValidate:
    def test_valid_output_passes(self):
        """A valid output should pass validation unchanged (except possible note truncation)."""
        output = make_valid_output()
        result = validate(output)

        assert result["top_themes"] == ["Performance", "UX", "Support"]
        assert len(result["quotes"]) == 3
        assert len(result["actions"]) == 3

    def test_truncates_note_over_250_words(self):
        """Note exceeding 250 words should be truncated to exactly 250."""
        long_note = " ".join(["word"] * 300)
        output = make_valid_output(note=long_note)

        result = validate(output)

        word_count = len(result["note"].split())
        assert word_count == 250

    def test_keeps_note_under_250_words(self):
        """Note under 250 words should remain unchanged."""
        short_note = "This is a short note with fewer than two hundred and fifty words."
        output = make_valid_output(note=short_note)

        result = validate(output)

        assert result["note"] == short_note

    def test_raises_if_top_themes_not_3(self):
        """Should raise if top_themes has fewer than 3 items."""
        output = make_valid_output(top_themes=["Theme1", "Theme2"])

        with pytest.raises(ValueError, match="Expected 3 top_themes"):
            validate(output)

    def test_raises_if_top_themes_more_than_3(self):
        """Should raise if top_themes has more than 3 items."""
        output = make_valid_output(top_themes=["A", "B", "C", "D"])

        with pytest.raises(ValueError, match="Expected 3 top_themes"):
            validate(output)

    def test_raises_if_quotes_not_3(self):
        """Should raise if quotes count != 3."""
        output = make_valid_output(quotes=[
            {"text": "Only one quote", "rating": 3},
        ])

        with pytest.raises(ValueError, match="Expected 3 quotes"):
            validate(output)

    def test_raises_if_actions_not_3(self):
        """Should raise if actions count != 3."""
        output = make_valid_output(actions=["Action 1"])

        with pytest.raises(ValueError, match="Expected 3 actions"):
            validate(output)

    def test_raises_if_themes_more_than_5(self):
        """Should raise if more than 5 themes."""
        themes = [
            {"name": f"Theme{i}", "description": f"Desc {i}", "review_count": i}
            for i in range(6)
        ]
        output = make_valid_output(themes=themes)

        with pytest.raises(ValueError, match="Too many themes"):
            validate(output)

    def test_allows_up_to_5_themes(self):
        """5 themes should be valid."""
        themes = [
            {"name": f"Theme{i}", "description": f"Desc {i}", "review_count": i}
            for i in range(5)
        ]
        output = make_valid_output(themes=themes)

        result = validate(output)

        assert len(result["themes"]) == 5

    def test_note_truncation_preserves_whole_words(self):
        """Truncation should cut at word boundaries, not mid-word."""
        # 251 words, each unique
        words = [f"word{i}" for i in range(251)]
        long_note = " ".join(words)
        output = make_valid_output(note=long_note)

        result = validate(output)

        result_words = result["note"].split()
        assert len(result_words) == 250
        assert result_words[-1] == "word249"
