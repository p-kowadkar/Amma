"""Tests for SessionRulingCache — grey zone memory cache from main.py."""
import pytest
from main import SessionRulingCache


class TestRulingCache:
    def test_set_and_get(self):
        cache = SessionRulingCache()
        cache.set("YouTube", "TIMEPASS")
        assert cache.get("YouTube") == "TIMEPASS"

    def test_get_nonexistent_returns_none(self):
        cache = SessionRulingCache()
        assert cache.get("NotHere") is None

    def test_normalize_lowercases(self):
        cache = SessionRulingCache()
        cache.set("YouTube", "TIMEPASS")
        assert cache.get("youtube") == "TIMEPASS"
        assert cache.get("YOUTUBE") == "TIMEPASS"

    def test_normalize_strips_whitespace(self):
        cache = SessionRulingCache()
        cache.set("  YouTube  ", "TIMEPASS")
        assert cache.get("YouTube") == "TIMEPASS"

    def test_normalize_replaces_spaces_with_dashes(self):
        cache = SessionRulingCache()
        cache.set("VS Code", "WORK")
        assert cache.get("vs-code") == "WORK"
        assert cache.get("VS Code") == "WORK"

    def test_overwrite_ruling(self):
        cache = SessionRulingCache()
        cache.set("YouTube", "GREY")
        cache.set("YouTube", "TIMEPASS")
        assert cache.get("YouTube") == "TIMEPASS"

    def test_multiple_entries(self):
        cache = SessionRulingCache()
        cache.set("YouTube", "TIMEPASS")
        cache.set("VS Code", "WORK")
        cache.set("Slack", "GREY")
        assert cache.get("YouTube") == "TIMEPASS"
        assert cache.get("VS Code") == "WORK"
        assert cache.get("Slack") == "GREY"

    def test_source_param_does_not_affect_lookup(self):
        cache = SessionRulingCache()
        cache.set("App", "WORK", source="gemini")
        cache.set("App2", "TIMEPASS", source="grey-timeout")
        assert cache.get("App") == "WORK"
        assert cache.get("App2") == "TIMEPASS"

    def test_empty_key(self):
        cache = SessionRulingCache()
        cache.set("", "WORK")
        assert cache.get("") == "WORK"
