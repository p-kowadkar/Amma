"""Tests for dialogue module — pools, line retrieval, volumes, snapback mapping."""
import pytest
from dialogue import DialoguePool, DIALOGUE_POOLS, get_line, get_volume, get_snapback_type


class TestDialoguePool:
    def test_next_returns_string(self):
        pool = DialoguePool(["a", "b", "c"])
        assert isinstance(pool.next(), str)

    def test_exhausts_all_before_reshuffling(self):
        lines = ["a", "b", "c"]
        pool = DialoguePool(lines)
        drawn = {pool.next() for _ in range(3)}
        assert drawn == set(lines)

    def test_reshuffles_after_exhaustion(self):
        lines = ["a", "b", "c"]
        pool = DialoguePool(lines)
        for _ in range(3):
            pool.next()
        # Should reshuffle and continue
        fourth = pool.next()
        assert fourth in lines

    def test_single_line_pool(self):
        pool = DialoguePool(["only"])
        assert pool.next() == "only"
        assert pool.next() == "only"

    def test_original_preserved_after_exhaustion(self):
        lines = ["x", "y", "z"]
        pool = DialoguePool(lines)
        for _ in range(10):
            pool.next()
        assert pool.original == lines


class TestGetLine:
    @pytest.mark.parametrize("itype", [
        "WARNING1", "WARNING2", "WARNING3", "WARNING4", "WARNING5",
        "NUCLEAR", "RESET_PRAISE", "RADIO",
        "SNAPBACK_1", "SNAPBACK_2", "SNAPBACK_3", "SNAPBACK_4", "SNAPBACK_5",
        "BREAK_CHECKIN_15", "BREAK_CHECKIN_30",
    ])
    def test_known_types_return_strings(self, itype):
        line = get_line(itype)
        assert isinstance(line, str)
        assert len(line) > 0

    def test_unknown_type_returns_fallback(self):
        assert get_line("NONEXISTENT") == "Beta. Focus."

    def test_grey_question_substitutes_app(self):
        line = get_line("GREY_QUESTION", app="YouTube")
        assert "YouTube" in line

    def test_grey_question_without_app(self):
        line = get_line("GREY_QUESTION", app="")
        assert isinstance(line, str)


class TestGetVolume:
    def test_warning_volumes_escalate(self):
        v1 = get_volume("WARNING1")
        v5 = get_volume("WARNING5")
        assert v1 < v5
        assert v5 == 1.00

    def test_nuclear_is_max_volume(self):
        assert get_volume("NUCLEAR") == 1.00

    def test_radio_is_quiet(self):
        assert get_volume("RADIO") <= 0.60

    def test_unknown_returns_default(self):
        assert get_volume("NONEXISTENT") == 0.70

    @pytest.mark.parametrize("itype,expected", [
        ("WARNING1", 0.60), ("WARNING2", 0.70), ("WARNING3", 0.80),
        ("WARNING4", 0.90), ("WARNING5", 1.00), ("NUCLEAR", 1.00),
        ("RESET_PRAISE", 0.70), ("RADIO", 0.55),
    ])
    def test_exact_volumes(self, itype, expected):
        assert get_volume(itype) == expected


class TestGetSnapbackType:
    @pytest.mark.parametrize("level,expected", [
        (1, "SNAPBACK_1"), (2, "SNAPBACK_2"), (3, "SNAPBACK_3"),
        (4, "SNAPBACK_4"), (5, "SNAPBACK_5"),
    ])
    def test_maps_level_to_snapback(self, level, expected):
        assert get_snapback_type(level) == expected

    def test_clamps_above_5(self):
        assert get_snapback_type(6) == "SNAPBACK_5"
        assert get_snapback_type(10) == "SNAPBACK_5"


class TestDialoguePools:
    def test_all_expected_pools_exist(self):
        expected = [
            "WARNING1", "WARNING2", "WARNING3", "WARNING4", "WARNING5",
            "NUCLEAR", "SNAPBACK_1", "SNAPBACK_2", "SNAPBACK_3",
            "SNAPBACK_4", "SNAPBACK_5", "RESET_PRAISE", "RADIO",
            "GREY_QUESTION", "BREAK_CHECKIN_15", "BREAK_CHECKIN_30",
        ]
        for key in expected:
            assert key in DIALOGUE_POOLS, f"Missing pool: {key}"

    def test_all_pools_have_at_least_one_line(self):
        for key, pool in DIALOGUE_POOLS.items():
            assert len(pool.original) >= 1, f"Empty pool: {key}"
