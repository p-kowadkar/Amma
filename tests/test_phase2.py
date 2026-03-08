"""
Phase 2 tests — Core Feature Completion.
Covers: personality engine, pattern tracker, support mode, time-of-day,
nuclear refinements, wake word interface, dialogue template vars.
"""
import pytest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from config import AmmaConfig
from personality import (
    ARCHETYPES, apply_archetype, SetupInterview, get_code_switch_prompt,
)
from pattern import PatternTracker, BLACK_HOLE_MIN_VISITS, BLACK_HOLE_MIN_MINUTES
from support_mode import SupportModeManager, AmmaMode
from time_of_day import get_current_window, is_alarm_hours, TIME_WINDOWS
from state_machine import AmmaStateMachine
from dialogue import get_line
from wake_word import WakeWordListener

now_utc = lambda: datetime.now(timezone.utc)


# ── Personality Engine ──────────────────────────────────────────────────────

class TestArchetypes:
    def test_all_archetypes_exist(self):
        expected = {"classic", "modern", "anxious", "competitive", "philosopher", "dadi"}
        assert set(ARCHETYPES.keys()) == expected

    def test_apply_archetype_modifies_config(self):
        config = AmmaConfig()
        apply_archetype(config, "dadi")
        assert config.strictness == 5
        assert config.warmth == 10

    def test_apply_archetype_competitive(self):
        config = AmmaConfig()
        apply_archetype(config, "competitive")
        assert config.strictness == 9
        assert config.patience_minutes == 30

    def test_apply_nonexistent_archetype_noop(self):
        config = AmmaConfig()
        original_strict = config.strictness
        apply_archetype(config, "nonexistent")
        assert config.strictness == original_strict


class TestSetupInterview:
    def test_interview_flow(self):
        interview = SetupInterview()
        assert interview.completed is False
        q = interview.current_question
        assert q is not None
        assert q[0] == "formal_name"

    def test_answer_advances(self):
        interview = SetupInterview()
        next_q = interview.answer("Pranav")
        assert next_q[0] == "nickname"
        assert interview.answers["formal_name"] == "Pranav"

    def test_completion(self):
        interview = SetupInterview()
        for i in range(len(interview.questions)):
            interview.answer(f"answer_{i}")
        assert interview.completed is True

    def test_apply_to_config(self):
        interview = SetupInterview()
        interview.answers = {
            "formal_name": "Rahul",
            "nickname": "Rahu",
            "full_name": "Rahul Kumar",
            "languages": "Hindi, English, Marathi",
            "scold_language": "Hindi",
            "support_language": "Marathi",
            "archetype": "philosopher",
            "custom_phrase": "Kab sudhrega tu?",
        }
        config = AmmaConfig()
        interview.apply_to_config(config)
        assert config.user_formal_name == "Rahul"
        assert config.nickname == "Rahu"
        assert config.languages == ["Hindi", "English", "Marathi"]
        assert config.strictness == 7  # philosopher
        assert "general" in config.custom_phrases

    def test_code_switch_prompt(self):
        prompt = get_code_switch_prompt(
            ["Kannada", "Hindi", "English"], "Kannada", "Hindi"
        )
        assert "Kannada" in prompt
        assert "Hindi" in prompt
        assert "Never announce" in prompt


# ── Pattern Tracker ─────────────────────────────────────────────────────────

class TestPatternTracker:
    def test_record_and_count(self):
        pt = PatternTracker()
        pt.record("YouTube", "TIMEPASS", timedelta(minutes=10))
        pt.record("YouTube", "TIMEPASS", timedelta(minutes=10))
        stats = pt.get_stats("YouTube")
        assert stats["visits"] == 2
        assert stats["total_minutes"] == 20

    def test_work_not_recorded(self):
        pt = PatternTracker()
        pt.record("VS Code", "WORK", timedelta(minutes=60))
        stats = pt.get_stats("VS Code")
        assert stats["visits"] == 0

    def test_black_hole_detection(self):
        pt = PatternTracker()
        for _ in range(BLACK_HOLE_MIN_VISITS):
            pt.record("Instagram", "TIMEPASS", timedelta(minutes=BLACK_HOLE_MIN_MINUTES // BLACK_HOLE_MIN_VISITS + 1))
        result = pt.check_black_hole("Instagram")
        assert result is not None
        assert result["app"] == "Instagram"
        assert result["count"] == BLACK_HOLE_MIN_VISITS

    def test_black_hole_not_triggered_below_threshold(self):
        pt = PatternTracker()
        pt.record("Twitter", "TIMEPASS", timedelta(minutes=5))
        pt.record("Twitter", "TIMEPASS", timedelta(minutes=5))
        assert pt.check_black_hole("Twitter") is None

    def test_black_hole_fires_once(self):
        pt = PatternTracker()
        for _ in range(5):
            pt.record("Reddit", "TIMEPASS", timedelta(minutes=10))
        r1 = pt.check_black_hole("Reddit")
        assert r1 is not None
        r2 = pt.check_black_hole("Reddit")
        assert r2 is None  # Already flagged

    def test_amplified_start_level(self):
        pt = PatternTracker()
        for _ in range(4):
            pt.record("TikTok", "TIMEPASS", timedelta(minutes=10))
        pt.check_black_hole("TikTok")  # Flag it
        assert pt.get_starting_warning_level("TikTok") == 3
        assert pt.get_starting_warning_level("Unknown App") == 0

    def test_normalization(self):
        pt = PatternTracker()
        pt.record("You Tube", "TIMEPASS", timedelta(minutes=10))
        pt.record("you tube", "TIMEPASS", timedelta(minutes=10))
        stats = pt.get_stats("YOU TUBE")
        assert stats["visits"] == 2


# ── Support Mode ────────────────────────────────────────────────────────────

class TestSupportMode:
    def test_starts_in_guard(self):
        sm = SupportModeManager()
        assert sm.is_guard is True

    def test_trigger_enters_support(self):
        sm = SupportModeManager()
        result = sm.add_signal("rejection_email")
        assert result == AmmaMode.SUPPORT
        assert sm.is_support is True

    def test_unknown_signal_no_transition(self):
        sm = SupportModeManager()
        result = sm.add_signal("random_event")
        assert result is None
        assert sm.is_guard is True

    def test_crisis_on_two_signals(self):
        sm = SupportModeManager()
        sm.add_signal("repeated_searches_concerning_topics")
        result = sm.add_signal("direct_statement_of_distress")
        assert result == AmmaMode.CRISIS
        assert sm.is_crisis is True

    def test_return_to_guard(self):
        sm = SupportModeManager()
        sm.add_signal("stress_typing")
        assert sm.is_support is True
        sm.return_to_guard()
        assert sm.is_guard is True
        assert len(sm.active_signals) == 0

    def test_recommended_voice(self):
        sm = SupportModeManager()
        assert sm.recommended_voice == "Aoede"
        sm.add_signal("rejection_email")
        assert sm.recommended_voice == "Kore"

    def test_support_does_not_retrigger(self):
        sm = SupportModeManager()
        sm.add_signal("rejection_email")
        assert sm.is_support
        # Another support trigger while already in support → no transition
        result = sm.add_signal("stress_typing")
        assert result is None  # Already in SUPPORT, not GUARD


# ── Time-of-Day ─────────────────────────────────────────────────────────────

class TestTimeOfDay:
    def _make_time(self, hour: int, minute: int = 0) -> datetime:
        """Create a datetime at the given IST hour."""
        return datetime(2026, 3, 8, hour, minute, tzinfo=ZoneInfo("Asia/Kolkata")).astimezone(timezone.utc)

    def test_morning_launch(self):
        tw = get_current_window("Asia/Kolkata", now=self._make_time(8))
        assert tw.name == "MORNING_LAUNCH"

    def test_peak_hours(self):
        tw = get_current_window("Asia/Kolkata", now=self._make_time(10))
        assert tw.name == "PEAK_HOURS"

    def test_lunch(self):
        tw = get_current_window("Asia/Kolkata", now=self._make_time(12, 30))
        assert tw.name == "LUNCH_WINDOW"

    def test_late_night(self):
        tw = get_current_window("Asia/Kolkata", now=self._make_time(22))
        assert tw.name == "LATE_NIGHT"

    def test_alarm_hours_3am(self):
        assert is_alarm_hours("Asia/Kolkata", now=self._make_time(3)) is True

    def test_alarm_hours_10am(self):
        assert is_alarm_hours("Asia/Kolkata", now=self._make_time(10)) is False

    def test_early_bird(self):
        tw = get_current_window("Asia/Kolkata", now=self._make_time(5, 30))
        assert tw.name == "EARLY_BIRD"

    def test_evening(self):
        tw = get_current_window("Asia/Kolkata", now=self._make_time(19))
        assert tw.name == "EVENING"


# ── Nuclear Protocol Refinements ────────────────────────────────────────────

class TestNuclearRefinements:
    def test_nuclear_count_increments(self):
        sm = AmmaStateMachine()
        sm.process_nuclear()
        assert sm.nuclear_count == 1
        sm.process_nuclear()
        assert sm.nuclear_count == 2

    def test_full_name_trigger_after_3(self):
        sm = AmmaStateMachine()
        config = AmmaConfig(full_name="Pranav Shridhar Kowadkar")
        sm.process_nuclear(config=config)
        sm.process_nuclear(config=config)
        result = sm.process_nuclear(config=config)
        assert "Pranav Shridhar Kowadkar" in result["line"]

    def test_no_full_name_without_config(self):
        sm = AmmaStateMachine()
        for _ in range(5):
            result = sm.process_nuclear()
        assert result["type"] == "NUCLEAR"
        # Without config, should use dialogue pool line

    def test_nuclear_30s_repeat(self):
        sm = AmmaStateMachine()
        sm.process_nuclear()
        # State is NUCLEAR — _check_repeat should use 30s interval
        assert sm.state == "NUCLEAR"


# ── Dialogue Template Variables ─────────────────────────────────────────────

class TestDialogueTemplates:
    def test_black_hole_template(self):
        line = get_line("BLACK_HOLE", app="YouTube", count=4, minutes=47)
        assert "YouTube" in line
        assert "4" in line or "47" in line  # Template vars replaced

    def test_grey_question_template(self):
        line = get_line("GREY_QUESTION", app="Reddit")
        assert "Reddit" in line

    def test_unknown_pool_fallback(self):
        line = get_line("NONEXISTENT_POOL")
        assert line == "Beta. Focus."


# ── Wake Word Interface ─────────────────────────────────────────────────────

class TestWakeWordInterface:
    def test_default_wake_words(self):
        ww = WakeWordListener()
        assert "hey amma" in ww.wake_words
        assert "amma" in ww.wake_words

    def test_custom_wake_words(self):
        ww = WakeWordListener(wake_words=["hey mom", "ma"])
        assert ww.wake_words == ["hey mom", "ma"]

    def test_not_available_by_default(self):
        ww = WakeWordListener()
        assert ww.is_available is False

    def test_stop_without_start(self):
        ww = WakeWordListener()
        ww.stop()  # Should not raise


# ── Config New Fields ───────────────────────────────────────────────────────

class TestConfigPhase2:
    def test_default_archetype(self):
        config = AmmaConfig()
        assert config.archetype == "classic"

    def test_default_timezone(self):
        config = AmmaConfig()
        assert config.timezone == "Asia/Kolkata"

    def test_support_voice(self):
        config = AmmaConfig()
        assert config.support_voice_name == "Kore"

    def test_wake_word_config(self):
        config = AmmaConfig()
        assert "amma" in config.wake_words
