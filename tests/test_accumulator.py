"""Tests for AmmaAccumulator — wall-clock tracking, escalation thresholds, breaks, demo mode."""
import pytest
from datetime import datetime, timedelta, timezone
from accumulator import AmmaAccumulator


def make_ts(minutes_offset: float = 0) -> datetime:
    """Create a UTC timestamp offset by N minutes from a fixed base."""
    base = datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc)
    return base + timedelta(minutes=minutes_offset)


def pump(acc, classification, total_minutes, start_offset=0, step=5):
    """Pump updates in small increments to stay under the 15-min gap cap.
    Returns the last update() result dict."""
    result = None
    n = int(total_minutes / step)
    for i in range(n):
        offset = start_offset + (i + 1) * step
        result = acc.update(classification, now=make_ts(offset))
    return result


class TestBasicAccumulation:
    def test_work_adds_to_work_total(self):
        acc = AmmaAccumulator(last_update=make_ts(0))
        acc.update("WORK", now=make_ts(1))
        assert acc.work_total == timedelta(minutes=1)
        assert acc.timepass_total == timedelta(0)

    def test_timepass_adds_to_timepass_total(self):
        acc = AmmaAccumulator(last_update=make_ts(0))
        acc.update("TIMEPASS", now=make_ts(2))
        assert acc.timepass_total == timedelta(minutes=2)
        assert acc.work_total == timedelta(0)

    def test_grey_does_not_accumulate(self):
        acc = AmmaAccumulator(last_update=make_ts(0))
        acc.update("GREY", now=make_ts(5))
        assert acc.work_total == timedelta(0)
        assert acc.timepass_total == timedelta(0)

    def test_multiple_updates_accumulate(self):
        acc = AmmaAccumulator(last_update=make_ts(0))
        acc.update("WORK", now=make_ts(1))
        acc.update("WORK", now=make_ts(2))
        acc.update("TIMEPASS", now=make_ts(3))
        assert acc.work_total == timedelta(minutes=2)
        assert acc.timepass_total == timedelta(minutes=1)


class TestGapCap:
    """If elapsed > 15 min between updates, elapsed is zeroed (sleep/away)."""

    def test_gap_over_15min_resets_to_zero(self):
        acc = AmmaAccumulator(last_update=make_ts(0))
        acc.update("WORK", now=make_ts(20))  # 20 min gap
        assert acc.work_total == timedelta(0)

    def test_gap_exactly_15min_is_normal(self):
        acc = AmmaAccumulator(last_update=make_ts(0))
        acc.update("WORK", now=make_ts(15))  # not > 15
        assert acc.work_total == timedelta(minutes=15)

    def test_gap_just_over_15min_caps(self):
        acc = AmmaAccumulator(last_update=make_ts(0))
        acc.update("TIMEPASS", now=make_ts(15.1))
        assert acc.timepass_total == timedelta(0)

    def test_last_update_still_advances_after_cap(self):
        """Even when elapsed is capped, last_update moves forward."""
        acc = AmmaAccumulator(last_update=make_ts(0))
        acc.update("WORK", now=make_ts(20))  # Gap capped
        acc.update("WORK", now=make_ts(25))  # 5 min from last → normal
        assert acc.work_total == timedelta(minutes=5)


class TestWarningLevels:
    """Spec thresholds: L1=45m, L2=60m, L3=75m, L4=90m, L5=105m.
    Threshold tests use skip_time_for_demo (bypasses gap cap).
    Intervention tests use incremental pumping (full update path)."""

    def test_below_45min_is_level_0(self):
        acc = AmmaAccumulator()
        acc.skip_time_for_demo(44)
        assert acc.warning_level == 0

    def test_at_45min_is_level_1(self):
        acc = AmmaAccumulator()
        acc.skip_time_for_demo(45)
        assert acc.warning_level == 1

    def test_at_60min_is_level_2(self):
        acc = AmmaAccumulator()
        acc.skip_time_for_demo(60)
        assert acc.warning_level == 2

    def test_at_75min_is_level_3(self):
        acc = AmmaAccumulator()
        acc.skip_time_for_demo(75)
        assert acc.warning_level == 3

    def test_at_90min_is_level_4(self):
        acc = AmmaAccumulator()
        acc.skip_time_for_demo(90)
        assert acc.warning_level == 4

    def test_at_105min_is_level_5(self):
        acc = AmmaAccumulator()
        acc.skip_time_for_demo(105)
        assert acc.warning_level == 5

    def test_level_change_fires_intervention_via_update(self):
        """Pump to 40 min, then one 5-min step → crosses 45 → WARNING1."""
        acc = AmmaAccumulator(last_update=make_ts(0))
        pump(acc, "TIMEPASS", 40)  # 8 x 5 min, last_update = make_ts(40)
        result = acc.update("TIMEPASS", now=make_ts(45))
        assert result["level_changed"] is True
        assert result["intervention"] == "WARNING1"

    def test_no_level_change_no_intervention(self):
        acc = AmmaAccumulator(last_update=make_ts(0))
        acc.update("TIMEPASS", now=make_ts(5))
        result = acc.update("TIMEPASS", now=make_ts(10))
        assert result["level_changed"] is False
        assert result["intervention"] is None

    def test_level_escalation_through_all_thresholds(self):
        """Walk from L0 → L5 via incremental pumping."""
        acc = AmmaAccumulator(last_update=make_ts(0))
        pump(acc, "TIMEPASS", 45)   # L1
        assert acc.warning_level == 1
        pump(acc, "TIMEPASS", 15, start_offset=45)   # +15 → 60 → L2
        assert acc.warning_level == 2
        pump(acc, "TIMEPASS", 15, start_offset=60)   # +15 → 75 → L3
        assert acc.warning_level == 3
        pump(acc, "TIMEPASS", 15, start_offset=75)   # +15 → 90 → L4
        assert acc.warning_level == 4
        pump(acc, "TIMEPASS", 15, start_offset=90)   # +15 → 105 → L5
        assert acc.warning_level == 5


class TestWorkStreak:
    def test_2h_work_streak_fires_reset_praise(self):
        acc = AmmaAccumulator(last_update=make_ts(0))
        result = pump(acc, "WORK", 120, step=10)  # 12 x 10 min
        assert result["intervention"] == "RESET_PRAISE"

    def test_reset_praise_clears_timepass(self):
        acc = AmmaAccumulator(last_update=make_ts(0))
        pump(acc, "TIMEPASS", 30)  # 6 x 5 min → 30 min timepass
        pump(acc, "WORK", 120, start_offset=30, step=10)  # 12 x 10 min work
        assert acc.timepass_total == timedelta(0)
        assert acc.warning_level == 0

    def test_timepass_resets_work_streak(self):
        acc = AmmaAccumulator(last_update=make_ts(0))
        acc.update("WORK", now=make_ts(10))  # 10 min work streak
        acc.update("TIMEPASS", now=make_ts(11))
        assert acc.work_streak == timedelta(0)

    def test_work_streak_accumulates_across_updates(self):
        acc = AmmaAccumulator(last_update=make_ts(0))
        acc.update("WORK", now=make_ts(5))
        acc.update("WORK", now=make_ts(10))
        assert acc.work_streak == timedelta(minutes=10)


class TestBreakMode:
    def test_break_pauses_accumulation(self):
        acc = AmmaAccumulator(last_update=make_ts(0))
        acc.start_break()
        result = acc.update("TIMEPASS", now=make_ts(5))
        assert acc.timepass_total == timedelta(0)
        assert result["intervention"] is None

    def test_end_break_resumes(self):
        acc = AmmaAccumulator(last_update=make_ts(0))
        acc.start_break()
        acc.update("WORK", now=make_ts(10))  # During break, last_update advances
        acc.end_break()
        acc.update("WORK", now=make_ts(11))  # 1 min since last break update
        assert acc.work_total == timedelta(minutes=1)

    def test_break_minutes_property(self):
        acc = AmmaAccumulator()
        assert acc.break_minutes == 0
        acc.start_break()
        assert acc.break_minutes >= 0

    def test_end_break_clears_break_start(self):
        acc = AmmaAccumulator()
        acc.start_break()
        assert acc.break_start is not None
        acc.end_break()
        assert acc.break_start is None
        assert acc.in_break is False


class TestDemoMode:
    def test_skip_time_advances_timepass(self):
        acc = AmmaAccumulator()
        acc.skip_time_for_demo(50)
        assert acc.timepass_minutes == 50
        assert acc.warning_level == 1

    def test_skip_to_level_5(self):
        acc = AmmaAccumulator()
        acc.skip_time_for_demo(105)
        assert acc.warning_level == 5

    def test_skip_incremental(self):
        acc = AmmaAccumulator()
        acc.skip_time_for_demo(45)
        assert acc.warning_level == 1
        acc.skip_time_for_demo(15)  # total 60
        assert acc.warning_level == 2

    def test_skip_does_not_affect_work(self):
        acc = AmmaAccumulator()
        acc.skip_time_for_demo(60)
        assert acc.work_total == timedelta(0)


class TestProperties:
    def test_timepass_minutes_truncates(self):
        acc = AmmaAccumulator(timepass_total=timedelta(minutes=42, seconds=30))
        assert acc.timepass_minutes == 42

    def test_work_minutes(self):
        acc = AmmaAccumulator(work_total=timedelta(hours=1, minutes=15))
        assert acc.work_minutes == 75

    def test_last_classification_tracks(self):
        acc = AmmaAccumulator(last_update=make_ts(0))
        acc.update("WORK", now=make_ts(1))
        assert acc.last_classification == "WORK"
        acc.update("TIMEPASS", now=make_ts(2))
        assert acc.last_classification == "TIMEPASS"
