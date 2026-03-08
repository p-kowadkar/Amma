"""Tests for classifier module — parse_classification JSON parsing and edge cases."""
import pytest
from classifier import parse_classification, ClassificationResult, CLASSIFICATION_PROMPT


class TestParseClassification:
    def test_valid_json(self):
        raw = '{"classification": "WORK", "confidence": 0.95, "reason": "IDE open", "nuclear": false, "dominant_app": "VS Code"}'
        result = parse_classification(raw)
        assert result.classification == "WORK"
        assert result.confidence == 0.95
        assert result.reason == "IDE open"
        assert result.nuclear is False
        assert result.dominant_app == "VS Code"

    def test_json_with_markdown_fences(self):
        raw = '```json\n{"classification": "TIMEPASS", "confidence": 0.88, "reason": "Netflix", "nuclear": false, "dominant_app": "Netflix"}\n```'
        result = parse_classification(raw)
        assert result.classification == "TIMEPASS"
        assert result.confidence == 0.88

    def test_json_with_leading_text(self):
        raw = 'Here is the result:\n{"classification": "GREY", "confidence": 0.55, "reason": "Unclear", "nuclear": false, "dominant_app": "Chrome"}'
        result = parse_classification(raw)
        assert result.classification == "GREY"
        assert result.confidence == 0.55

    def test_json_with_trailing_text(self):
        raw = '{"classification": "WORK", "confidence": 0.90, "reason": "coding", "nuclear": false, "dominant_app": "PyCharm"}\nEnd of response.'
        result = parse_classification(raw)
        assert result.classification == "WORK"

    def test_missing_classification_defaults_to_grey(self):
        raw = '{"confidence": 0.5, "reason": "unknown", "nuclear": false, "dominant_app": "X"}'
        result = parse_classification(raw)
        assert result.classification == "GREY"

    def test_missing_confidence_defaults_to_half(self):
        raw = '{"classification": "WORK", "reason": "code", "nuclear": false, "dominant_app": "IDE"}'
        result = parse_classification(raw)
        assert result.confidence == 0.5

    def test_missing_nuclear_defaults_to_false(self):
        raw = '{"classification": "WORK", "confidence": 0.9, "reason": "ok", "dominant_app": "IDE"}'
        result = parse_classification(raw)
        assert result.nuclear is False

    def test_missing_dominant_app_defaults_to_unknown(self):
        raw = '{"classification": "WORK", "confidence": 0.9, "reason": "ok", "nuclear": false}'
        result = parse_classification(raw)
        assert result.dominant_app == "Unknown"

    def test_nuclear_true(self):
        raw = '{"classification": "TIMEPASS", "confidence": 0.99, "reason": "NSFW", "nuclear": true, "dominant_app": "Browser"}'
        result = parse_classification(raw)
        assert result.nuclear is True

    def test_confidence_as_string_is_coerced(self):
        raw = '{"classification": "WORK", "confidence": "0.85", "reason": "ok", "nuclear": false, "dominant_app": "X"}'
        result = parse_classification(raw)
        assert result.confidence == 0.85

    def test_invalid_json_raises(self):
        with pytest.raises(Exception):
            parse_classification("not json at all")

    def test_empty_string_raises(self):
        with pytest.raises(Exception):
            parse_classification("")

    def test_whitespace_padded_json(self):
        raw = '   \n  {"classification": "WORK", "confidence": 0.9, "reason": "ok", "nuclear": false, "dominant_app": "IDE"}  \n  '
        result = parse_classification(raw)
        assert result.classification == "WORK"


class TestClassificationResult:
    def test_dataclass_fields(self):
        r = ClassificationResult("WORK", 0.9, "coding", False, "VS Code")
        assert r.classification == "WORK"
        assert r.confidence == 0.9
        assert r.reason == "coding"
        assert r.nuclear is False
        assert r.dominant_app == "VS Code"


class TestPromptTemplate:
    def test_prompt_has_placeholders(self):
        assert "{window_title}" in CLASSIFICATION_PROMPT
        assert "{process_name}" in CLASSIFICATION_PROMPT

    def test_prompt_mentions_all_classifications(self):
        for cls in ("WORK", "GREY", "TIMEPASS"):
            assert cls in CLASSIFICATION_PROMPT

    def test_prompt_mentions_nuclear(self):
        assert "nuclear" in CLASSIFICATION_PROMPT.lower()
