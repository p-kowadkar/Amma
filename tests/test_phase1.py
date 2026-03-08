"""
Phase 1 tests — MVP Hardening features.
Covers: confidence threshold, debounce, 12h session cap, break manager,
grey zone streak preservation, peak warning tracking, longest streak tracking.
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from accumulator import AmmaAccumulator
from classifier import parse_classification, CONFIDENCE_THRESHOLD
from state_machine import AmmaStateMachine
from break_manager import BreakModeManager, BREAK_AUTO_EXPIRE_MINUTES

now_utc = lambda: datetime.now(timezone.utc)


# ── Confidence threshold enforcement ────────────────────────────────────────

class TestConfidenceThreshold:
    def test_low_confidence_forced_to_grey(self):
        raw = '{"classification": "WORK", "confidence": 0.50, "reason": "unclear", "nuclear": false, "dominant_app": "Chrome"}'
        r = parse_classification(raw)
        assert r.classification == "GREY"

    def test_exactly_at_threshold_is_not_grey(self):
        raw = '{"classification": "WORK", "confidence": 0.70, "reason": "IDE open", "nuclear": false, "dominant_app": "VS Code"}'
        r = parse_classification(raw)
        assert r.classification == "WORK"

    def test_above_threshold_passes_through(self):
        raw = '{"classification": "TIMEPASS", "confidence": 0.95, "reason": "Netflix", "nuclear": false, "dominant_app": "Netflix"}'
        r = parse_classification(raw)
        assert r.classification == "TIMEPASS"

    def test_nuclear_bypasses_threshold(self):
        """Nuclear content should stay TIMEPASS-classified even with low confidence."""
        raw = '{"classification": "TIMEPASS", "confidence": 0.40, "reason": "NSFW", "nuclear": true, "dominant_app": "Browser"}'
        r = parse_classification(raw)
        # Nuclear flag is set; classification is whatever the model said, not forced GREY
        assert r.nuclear is True
        assert r.classification == "TIMEPASS"

    def test_grey_with_low_confidence_stays_grey(self):
        raw = '{"classification": "GREY", "confidence": 0.30, "reason": "unclear", "nuclear": false, "dominant_app": "Browser"}'
        r = parse_classification(raw)
        assert r.classification == "GREY"

    def test_confidence_0_forced_grey(self):
        raw = '{"classification": "WORK", "confidence": 0.0, "reason": "no idea", "nuclear": false, "dominant_app": "Unknown"}'
        r = parse_classification(raw)
        assert r.classification == "GREY"


# ── Debounce (Ch 34.3) ─────────────────────────────────────────────────────

class TestDebounce:
    def make_sm(self, debounce=30):
        return AmmaStateMachine(debounce_seconds=debounce)

    def test_first_classification_accepted_immediately(self):
        sm = self.make_sm()
        t0 = now_utc()
        result = sm.process("WORK", now=t0)
        assert sm._confirmed_cls == "WORK"

    def test_same_classification_continues(self):
        sm = self.make_sm()
        t0 = now_utc()
        sm.process("WORK", now=t0)
        sm.process("WORK", now=t0 + timedelta(seconds=5))
        assert sm._confirmed_cls == "WORK"
        assert sm.state == "WORKING"

    def test_different_classification_debounced(self):
        sm = self.make_sm()
        t0 = now_utc()
        sm.process("WORK", now=t0)
        # Switch to TIMEPASS — should be debounced (no accumulation)
        result = sm.process("TIMEPASS", now=t0 + timedelta(seconds=5))
        assert result is None  # debouncing
        assert sm._confirmed_cls == "WORK"  # still WORK

    def test_debounce_completes_after_duration(self):
        sm = self.make_sm()
        t0 = now_utc()
        sm.process("WORK", now=t0)
        # Start debounce
        sm.process("TIMEPASS", now=t0 + timedelta(seconds=5))
        assert sm._confirmed_cls == "WORK"
        # 30 seconds later, same TIMEPASS → debounce passes
        sm.process("TIMEPASS", now=t0 + timedelta(seconds=35))
        assert sm._confirmed_cls == "TIMEPASS"

    def test_debounce_resets_on_new_classification(self):
        sm = self.make_sm()
        t0 = now_utc()
        sm.process("WORK", now=t0)
        sm.process("TIMEPASS", now=t0 + timedelta(seconds=5))
        # Before 30s, switch to GREY — resets debounce
        sm.process("GREY", now=t0 + timedelta(seconds=20))
        # TIMEPASS debounce is gone, now GREY is pending
        assert sm._pending_cls == "GREY"
        assert sm._confirmed_cls == "WORK"

    def test_no_debounce_when_disabled(self):
        sm = AmmaStateMachine(debounce_seconds=0)
        t0 = now_utc()
        sm.process("WORK", now=t0)
        sm.process("TIMEPASS", now=t0 + timedelta(seconds=5))
        # Without debounce, TIMEPASS should be processed immediately
        # (accumulator sees it, but might not trigger a level change yet)
        assert sm.last_classification == "TIMEPASS"

    def test_debounce_does_not_accumulate_time(self):
        """During debounce, no time should be counted toward either accumulator."""
        sm = self.make_sm()
        t0 = now_utc()
        sm.process("WORK", now=t0)
        sm.process("WORK", now=t0 + timedelta(seconds=5))
        work_before = sm.accumulator.work_total
        # Start debounce to TIMEPASS
        sm.process("TIMEPASS", now=t0 + timedelta(seconds=10))
        sm.process("TIMEPASS", now=t0 + timedelta(seconds=20))
        # During debounce, neither accumulator should grow
        assert sm.accumulator.timepass_total == timedelta(0)
        # Work should not have grown during debounce either
        assert sm.accumulator.work_total == work_before

    def test_rapid_flicker_ignored(self):
        """WORK → TIMEPASS → WORK in 10s should not register TIMEPASS."""
        sm = self.make_sm()
        t0 = now_utc()
        sm.process("WORK", now=t0)
        sm.process("TIMEPASS", now=t0 + timedelta(seconds=3))  # debouncing
        sm.process("WORK", now=t0 + timedelta(seconds=6))  # back to confirmed
        assert sm._confirmed_cls == "WORK"
        assert sm.accumulator.timepass_total == timedelta(0)


# ── Session cap ─────────────────────────────────────────────────────────────

class TestSessionCap:
    def test_session_not_exceeded_early(self):
        acc = AmmaAccumulator()
        assert acc.session_exceeded(12) is False

    def test_session_exceeded_after_cap(self):
        acc = AmmaAccumulator()
        acc.session_start = now_utc() - timedelta(hours=13)
        assert acc.session_exceeded(12) is True

    def test_session_exactly_at_cap(self):
        acc = AmmaAccumulator()
        acc.session_start = now_utc() - timedelta(hours=12)
        assert acc.session_exceeded(12) is True

    def test_custom_cap(self):
        acc = AmmaAccumulator()
        acc.session_start = now_utc() - timedelta(hours=3)
        assert acc.session_exceeded(2) is True
        assert acc.session_exceeded(4) is False


# ── Peak warning and longest streak tracking ────────────────────────────────

class TestTrackingStats:
    def pump(self, acc, classification, minutes, start):
        """Feed classification in 5-second increments for `minutes` minutes."""
        t = start
        for _ in range(minutes * 12):  # 12 ticks per minute at 5s
            t += timedelta(seconds=5)
            acc.update(classification, now=t)
        return t

    def test_peak_warning_tracked(self):
        acc = AmmaAccumulator()
        t = now_utc()
        t = self.pump(acc, "TIMEPASS", 50, t)  # Level 1
        assert acc.peak_warning_level >= 1
        t = self.pump(acc, "TIMEPASS", 20, t)  # Level 2
        assert acc.peak_warning_level >= 2
        # Reset
        acc._reset_scold_counter(t)
        assert acc.warning_level == 0
        # Peak should still be 2
        assert acc.peak_warning_level >= 2

    def test_longest_work_streak_tracked(self):
        acc = AmmaAccumulator()
        t = now_utc()
        t = self.pump(acc, "WORK", 30, t)
        assert acc.longest_work_streak_minutes >= 29  # Allow minor rounding

    def test_streak_survives_timepass(self):
        """Longest streak should be preserved even after timepass resets current streak."""
        acc = AmmaAccumulator()
        t = now_utc()
        t = self.pump(acc, "WORK", 20, t)
        longest_after_first = acc.longest_work_streak
        t = self.pump(acc, "TIMEPASS", 5, t)  # Resets current streak
        assert acc.work_streak == timedelta(0)
        assert acc.longest_work_streak == longest_after_first

    def test_grey_preserves_work_streak(self):
        """GREY should NOT reset work_streak (Ch 34.1)."""
        acc = AmmaAccumulator()
        t = now_utc()
        t = self.pump(acc, "WORK", 10, t)
        streak_before = acc.work_streak
        assert streak_before > timedelta(0)
        # Grey zone — should not touch streak
        t += timedelta(seconds=5)
        acc.update("GREY", now=t)
        assert acc.work_streak == streak_before


# ── Break Manager ───────────────────────────────────────────────────────────

class TestBreakManager:
    def test_activate_deactivate(self):
        acc = AmmaAccumulator()
        bm = BreakModeManager(acc)
        bm.activate()
        assert bm.is_active is True
        assert acc.in_break is True
        bm.deactivate()
        assert bm.is_active is False
        assert acc.in_break is False

    def test_no_intervention_early(self):
        acc = AmmaAccumulator()
        bm = BreakModeManager(acc)
        t0 = now_utc()
        bm.activate(now=t0)
        # 10 minutes in — no check-in yet
        result = bm.get_pending_intervention(now=t0 + timedelta(minutes=10))
        assert result is None

    def test_15min_checkin(self):
        acc = AmmaAccumulator()
        bm = BreakModeManager(acc)
        t0 = now_utc()
        bm.activate(now=t0)
        result = bm.get_pending_intervention(now=t0 + timedelta(minutes=16))
        assert result is not None
        assert result["type"] == "BREAK_CHECKIN_15"

    def test_30min_checkin(self):
        acc = AmmaAccumulator()
        bm = BreakModeManager(acc)
        t0 = now_utc()
        bm.activate(now=t0)
        # Fire 15 first
        bm.get_pending_intervention(now=t0 + timedelta(minutes=16))
        # Then 30
        result = bm.get_pending_intervention(now=t0 + timedelta(minutes=31))
        assert result is not None
        assert result["type"] == "BREAK_CHECKIN_30"

    def test_45min_checkin(self):
        acc = AmmaAccumulator()
        bm = BreakModeManager(acc)
        t0 = now_utc()
        bm.activate(now=t0)
        bm.get_pending_intervention(now=t0 + timedelta(minutes=16))
        bm.get_pending_intervention(now=t0 + timedelta(minutes=31))
        result = bm.get_pending_intervention(now=t0 + timedelta(minutes=46))
        assert result is not None
        assert result["type"] == "BREAK_CHECKIN_45"

    def test_60min_checkin(self):
        acc = AmmaAccumulator()
        bm = BreakModeManager(acc)
        t0 = now_utc()
        bm.activate(now=t0)
        bm.get_pending_intervention(now=t0 + timedelta(minutes=16))
        bm.get_pending_intervention(now=t0 + timedelta(minutes=31))
        bm.get_pending_intervention(now=t0 + timedelta(minutes=46))
        result = bm.get_pending_intervention(now=t0 + timedelta(minutes=61))
        assert result is not None
        assert result["type"] == "BREAK_CHECKIN_60"

    def test_auto_expire_at_75min(self):
        acc = AmmaAccumulator()
        bm = BreakModeManager(acc)
        t0 = now_utc()
        bm.activate(now=t0)
        result = bm.get_pending_intervention(now=t0 + timedelta(minutes=76))
        assert result is not None
        assert result["type"] == "BREAK_EXPIRED"
        assert bm.is_active is False
        assert acc.in_break is False

    def test_checkin_fires_only_once(self):
        acc = AmmaAccumulator()
        bm = BreakModeManager(acc)
        t0 = now_utc()
        bm.activate(now=t0)
        r1 = bm.get_pending_intervention(now=t0 + timedelta(minutes=16))
        assert r1["type"] == "BREAK_CHECKIN_15"
        # Same time again — should not fire again
        r2 = bm.get_pending_intervention(now=t0 + timedelta(minutes=17))
        # Should get BREAK_CHECKIN_30 only after 30 min, not another 15
        assert r2 is None

    def test_inactive_returns_none(self):
        acc = AmmaAccumulator()
        bm = BreakModeManager(acc)
        assert bm.get_pending_intervention() is None


# ── Startup checks ──────────────────────────────────────────────────────────

class TestStartupChecks:
    def test_missing_api_key_warns(self):
        from config import AmmaConfig
        from main import startup_checks
        config = AmmaConfig(gemini_api_key="")
        warnings = startup_checks(config)
        assert any("GEMINI_API_KEY" in w for w in warnings)

    def test_short_api_key_warns(self):
        from config import AmmaConfig
        from main import startup_checks
        config = AmmaConfig(gemini_api_key="abc")
        warnings = startup_checks(config)
        assert any("too short" in w for w in warnings)

    def test_valid_config_minimal_warnings(self):
        from config import AmmaConfig
        from main import startup_checks
        config = AmmaConfig(gemini_api_key="a" * 40)
        # May still warn about pywin32/pygame, but not API key
        warnings = startup_checks(config)
        assert not any("GEMINI_API_KEY" in w for w in warnings)
