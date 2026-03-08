"""Tests for AmmaStateMachine — state transitions, snap-back, nuclear, repeats, break."""
import pytest
from datetime import datetime, timedelta, timezone
from state_machine import AmmaStateMachine, WARNING_STATES


def now_utc():
    return datetime.now(timezone.utc)


def setup_sm_at_level(level: int) -> AmmaStateMachine:
    """Create a state machine already in a warning state at the given level."""
    sm = AmmaStateMachine()
    thresholds = {1: 45, 2: 60, 3: 75, 4: 90, 5: 105}
    sm.accumulator.skip_time_for_demo(thresholds[level])
    sm.accumulator.last_update = now_utc()
    sm.state = f"WARNING{level}" if level < 5 else "SCREAM"
    return sm


# ── Basic state transitions ──────────────────────────────────────────────

class TestStateTransitions:
    def test_idle_to_working_on_work(self):
        sm = AmmaStateMachine()
        sm.accumulator.last_update = now_utc()
        sm.process("WORK")
        assert sm.state == "WORKING"

    def test_grey_sets_grey_pending(self):
        sm = AmmaStateMachine()
        sm.accumulator.last_update = now_utc()
        sm.process("GREY")
        assert sm.state == "GREY_PENDING"

    def test_timepass_under_threshold_stays_working(self):
        sm = AmmaStateMachine()
        sm.accumulator.last_update = now_utc()
        sm.process("TIMEPASS")
        # Timepass total is microseconds, level = 0 → state = "WORKING"
        assert sm.state == "WORKING"

    def test_break_sets_break(self):
        sm = AmmaStateMachine()
        sm.accumulator.last_update = now_utc()
        sm.process("BREAK")
        assert sm.state == "BREAK"


# ── Snap-back detection ──────────────────────────────────────────────────

class TestSnapBack:
    def test_snapback_from_warning1(self):
        sm = setup_sm_at_level(1)
        result = sm.process("WORK")
        assert result is not None
        assert result["type"] == "SNAPBACK_1"
        assert sm.state == "WORKING"

    def test_snapback_from_warning3(self):
        sm = setup_sm_at_level(3)
        result = sm.process("WORK")
        assert result is not None
        assert result["type"] == "SNAPBACK_3"
        assert sm.state == "WORKING"

    def test_snapback_from_scream(self):
        sm = setup_sm_at_level(5)
        result = sm.process("WORK")
        assert result is not None
        assert result["type"] == "SNAPBACK_5"
        assert sm.state == "WORKING"

    def test_snapback_from_nuclear(self):
        sm = AmmaStateMachine()
        sm.process_nuclear()  # Sets state = "NUCLEAR"
        sm.accumulator.last_update = now_utc()
        result = sm.process("WORK")
        assert result is not None
        # accumulator.warning_level = 0, max(0, 1) = 1
        assert result["type"] == "SNAPBACK_1"
        assert sm.state == "WORKING"

    def test_snapback_has_line_and_volume(self):
        sm = setup_sm_at_level(2)
        result = sm.process("WORK")
        assert "line" in result
        assert "volume" in result
        assert isinstance(result["line"], str)
        assert isinstance(result["volume"], float)

    def test_no_snapback_from_working(self):
        sm = AmmaStateMachine()
        sm.state = "WORKING"
        sm.accumulator.last_update = now_utc()
        result = sm.process("WORK")
        # WORKING is not in WARNING_STATES → no snap-back
        assert result is None


# ── Level escalation via state machine ────────────────────────────────────

class TestLevelEscalation:
    def test_crosses_level_1_threshold(self):
        sm = AmmaStateMachine()
        # Set timepass at exactly threshold, but warning_level still 0
        sm.accumulator.timepass_total = timedelta(minutes=45)
        sm.accumulator.warning_level = 0
        sm.accumulator.last_update = now_utc()
        result = sm.process("TIMEPASS")
        assert result is not None
        assert result["type"] == "WARNING1"
        assert sm.state == "WARNING1"

    def test_level_5_maps_to_scream_state(self):
        sm = AmmaStateMachine()
        sm.accumulator.timepass_total = timedelta(minutes=105)
        sm.accumulator.warning_level = 4
        sm.accumulator.last_update = now_utc()
        result = sm.process("TIMEPASS")
        assert result is not None
        assert result["type"] == "WARNING5"
        assert sm.state == "SCREAM"

    def test_intervention_includes_line_and_volume(self):
        sm = AmmaStateMachine()
        sm.accumulator.timepass_total = timedelta(minutes=60)
        sm.accumulator.warning_level = 1
        sm.accumulator.last_update = now_utc()
        result = sm.process("TIMEPASS")
        assert result is not None
        assert isinstance(result["line"], str)
        assert len(result["line"]) > 0


# ── Nuclear ───────────────────────────────────────────────────────────────

class TestNuclear:
    def test_nuclear_sets_state(self):
        sm = AmmaStateMachine()
        sm.process_nuclear()
        assert sm.state == "NUCLEAR"

    def test_nuclear_returns_intervention(self):
        sm = AmmaStateMachine()
        result = sm.process_nuclear()
        assert result["type"] == "NUCLEAR"
        assert isinstance(result["line"], str)
        assert result["volume"] == 1.00

    def test_nuclear_sets_intervention_ts(self):
        sm = AmmaStateMachine()
        sm.process_nuclear()
        assert sm.last_intervention_ts is not None


# ── Repeat mechanism ─────────────────────────────────────────────────────

class TestRepeat:
    def test_repeat_fires_when_no_prior_intervention(self):
        sm = AmmaStateMachine()
        sm.state = "WARNING1"
        sm.accumulator.warning_level = 1
        sm.accumulator.timepass_total = timedelta(minutes=46)
        sm.accumulator.last_update = now_utc()
        # last_intervention_ts is None → repeat should fire
        result = sm.process("TIMEPASS")
        assert result is not None
        assert result["type"] == "WARNING1"

    def test_repeat_suppressed_within_interval(self):
        sm = AmmaStateMachine()
        sm.state = "WARNING1"
        sm.accumulator.warning_level = 1
        sm.accumulator.timepass_total = timedelta(minutes=46)
        sm.accumulator.last_update = now_utc()
        sm.last_intervention_ts = now_utc()  # Just fired
        result = sm.process("TIMEPASS")
        assert result is None

    def test_repeat_fires_after_interval_expired(self):
        sm = AmmaStateMachine()
        sm.state = "WARNING1"
        sm.accumulator.warning_level = 1
        sm.accumulator.timepass_total = timedelta(minutes=46)
        sm.accumulator.last_update = now_utc()
        # Set last intervention 11 min ago (interval for L1 = 10 min)
        sm.last_intervention_ts = now_utc() - timedelta(minutes=11)
        result = sm.process("TIMEPASS")
        assert result is not None
        assert result["type"] == "WARNING1"

    def test_level_5_repeat_interval_is_2min(self):
        sm = AmmaStateMachine()
        sm.state = "SCREAM"
        sm.accumulator.warning_level = 5
        sm.accumulator.timepass_total = timedelta(minutes=110)
        sm.accumulator.last_update = now_utc()
        # 3 min ago, level 5 interval = 2 min → should fire
        sm.last_intervention_ts = now_utc() - timedelta(minutes=3)
        result = sm.process("TIMEPASS")
        assert result is not None
        assert result["type"] == "WARNING5"


# ── Break mode ────────────────────────────────────────────────────────────

class TestBreak:
    def test_start_break(self):
        sm = AmmaStateMachine()
        sm.start_break()
        assert sm.state == "BREAK"
        assert sm.accumulator.in_break is True

    def test_end_break(self):
        sm = AmmaStateMachine()
        sm.start_break()
        sm.end_break()
        assert sm.state == "WORKING"
        assert sm.accumulator.in_break is False


# ── Reset praise ──────────────────────────────────────────────────────────

class TestResetPraise:
    def test_reset_praise_fires_through_state_machine(self):
        sm = AmmaStateMachine()
        # Set work_streak at 119:59, then give 2s of real elapsed to push over 2h
        sm.accumulator.work_streak = timedelta(minutes=119, seconds=59)
        sm.accumulator.last_update = now_utc() - timedelta(seconds=2)
        result = sm.process("WORK")
        # 119:59 + ~2s >= 2h → fires RESET_PRAISE
        assert result is not None
        assert result["type"] == "RESET_PRAISE"
        assert sm.state == "RESET"


# ── WARNING_STATES constant ──────────────────────────────────────────────

class TestConstants:
    def test_warning_states_includes_all_levels(self):
        for level in range(1, 5):
            assert f"WARNING{level}" in WARNING_STATES
        assert "SCREAM" in WARNING_STATES
        assert "NUCLEAR" in WARNING_STATES

    def test_warning_states_excludes_non_warnings(self):
        assert "WORKING" not in WARNING_STATES
        assert "IDLE" not in WARNING_STATES
        assert "BREAK" not in WARNING_STATES
