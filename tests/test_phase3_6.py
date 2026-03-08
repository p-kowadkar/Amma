"""
Tests for Phase 3-6 modules.
behavioral_signals, phone_protocol, integrations, mentor, social, parent_portal,
emotional, gamification, smriti, deployment.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timezone, timedelta, date


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — Behavioral Signals
# ═══════════════════════════════════════════════════════════════════════════════

class TestBehavioralSignals:
    def test_signal_creation(self):
        from behavioral_signals import Signal
        s = Signal(category="app", name="incognito", weight=5)
        assert s.weight == 5
        assert s.timestamp  # Auto-filled

    def test_risk_score_empty(self):
        from behavioral_signals import calculate_risk_score
        assert calculate_risk_score([]) == 0

    def test_risk_score_low(self):
        from behavioral_signals import Signal, calculate_risk_score
        signals = [Signal("app", "browser", 1)]
        assert calculate_risk_score(signals) == 1

    def test_risk_score_high(self):
        from behavioral_signals import Signal, calculate_risk_score
        signals = [
            Signal("app", "incognito", 5),
            Signal("app", "dating", 4),
            Signal("time", "late_night", 2),
            Signal("behavioral", "doom_scroll", 3),
        ]
        assert calculate_risk_score(signals) == 5

    def test_classify_risk_adult(self):
        from behavioral_signals import Signal, classify_risk_category
        signals = [Signal("app", "incognito", 5)]
        assert classify_risk_category(signals) == "adult"

    def test_classify_risk_social(self):
        from behavioral_signals import Signal, classify_risk_category
        signals = [Signal("app", "social_feed", 2)]
        assert classify_risk_category(signals) == "social"

    def test_phone_report_privacy(self):
        from behavioral_signals import Signal, build_phone_report
        signals = [Signal("app", "dating", 4)]
        report = build_phone_report(signals)
        assert "risk_level" in report
        assert "category" in report
        assert "timestamp" in report
        # Must NOT contain raw signal data
        assert "dating" not in str(report.get("risk_level"))


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — Phone Protocol
# ═══════════════════════════════════════════════════════════════════════════════

class TestPhoneProtocol:
    def test_phone_event_safe_dict(self):
        from phone_protocol import PhoneEvent, PhoneEventType
        evt = PhoneEvent(
            event_type=PhoneEventType.HEARTBEAT,
            risk_level=2, category="social",
        )
        safe = evt.to_safe_dict()
        assert safe["risk_level"] == 2
        assert "device_state" not in safe

    def test_classify_app_known(self):
        from phone_protocol import classify_app
        result = classify_app("com.tinder")
        assert result["risk"] == 4

    def test_classify_app_unknown(self):
        from phone_protocol import classify_app
        result = classify_app("com.unknown.app")
        assert result["risk"] == 1

    def test_classify_url_adult(self):
        from phone_protocol import classify_url
        result = classify_url("https://www.pornhub.com/something")
        assert result["category"] == "adult"

    def test_classify_url_work(self):
        from phone_protocol import classify_url
        result = classify_url("https://github.com/user/repo")
        assert result["category"] == "work"

    def test_contradiction_work_phone(self):
        from phone_protocol import CrossDeviceState, detect_contradictions
        state = CrossDeviceState(
            laptop_classification="WORK", phone_risk_level=4,
        )
        contradictions = detect_contradictions(state)
        assert len(contradictions) == 1
        assert contradictions[0]["type"] == "WORK_PHONE_CONTRADICTION"

    def test_contradiction_blind_spot(self):
        from phone_protocol import CrossDeviceState, detect_contradictions
        state = CrossDeviceState(
            laptop_classification="UNKNOWN", phone_risk_level=5,
        )
        contradictions = detect_contradictions(state)
        assert any(c["type"] == "BLIND_SPOT_CAUGHT" for c in contradictions)

    def test_no_contradiction_when_aligned(self):
        from phone_protocol import CrossDeviceState, detect_contradictions
        state = CrossDeviceState(
            laptop_classification="WORK", phone_risk_level=1,
        )
        assert detect_contradictions(state) == []

    def test_location_classify_home(self):
        from phone_protocol import LocationProfile, classify_location
        profile = LocationProfile(home_coords=(40.7128, -74.0060))
        result = classify_location(40.7128, -74.0060, profile)
        assert result == "home"


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4 — Integrations
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrations:
    def test_calendar_event_classify_interview(self):
        from integrations import CalendarEvent
        evt = CalendarEvent(
            title="Google Interview Round 2",
            start=datetime.now(timezone.utc),
            end=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert evt.classify() == "INTERVIEW"

    def test_calendar_event_classify_meeting(self):
        from integrations import CalendarEvent
        evt = CalendarEvent(
            title="Team standup", attendees=5,
            start=datetime.now(timezone.utc),
            end=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        assert evt.classify() == "MEETING"

    def test_email_classify_rejection(self):
        from integrations import EmailEvent
        evt = EmailEvent(
            subject="Unfortunately we will not be moving forward",
            sender_domain="google.com",
            timestamp=datetime.now(timezone.utc),
        )
        assert evt.classify() == "REJECTION"

    def test_email_classify_offer(self):
        from integrations import EmailEvent
        evt = EmailEvent(
            subject="Congratulations! Your offer letter",
            sender_domain="meta.com",
            timestamp=datetime.now(timezone.utc),
        )
        assert evt.classify() == "OFFER"

    def test_notification_queue_holds_social(self):
        from integrations import NotificationQueue, Notification
        q = NotificationQueue()
        notif = Notification(app="WhatsApp", title="New message", body="Hey!")
        delivered = q.process(notif, "WORKING")
        assert not delivered
        assert len(q.held) == 1

    def test_notification_queue_delivers_critical(self):
        from integrations import NotificationQueue, Notification
        q = NotificationQueue()
        notif = Notification(app="Phone", title="Mom calling", body="urgent")
        delivered = q.process(notif, "WORKING")
        assert delivered

    def test_music_mood_sad(self):
        from integrations import MusicContext
        ctx = MusicContext(playlist_name="Sad Songs Collection", is_playing=True)
        assert ctx.mood_signal == "melancholy"

    def test_music_mood_focus(self):
        from integrations import MusicContext
        ctx = MusicContext(playlist_name="Lo-fi study beats", is_playing=True)
        assert ctx.mood_signal == "focus"

    def test_health_stress_high(self):
        from integrations import HealthSnapshot
        h = HealthSnapshot(resting_hr=65, current_hr=95)
        assert h.stress_level == "HIGH_STRESS"

    def test_life_context_support_mode(self):
        from integrations import LifeContext
        ctx = LifeContext(
            email_sentiment="negative",
            music_mood="melancholy",
            health_status="stressed",
        )
        assert ctx.recommended_mode() == "SUPPORT"

    def test_life_context_guard(self):
        from integrations import LifeContext
        ctx = LifeContext()
        assert ctx.recommended_mode() == "GUARD"


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4 — Mentor Mode
# ═══════════════════════════════════════════════════════════════════════════════

class TestMentor:
    def test_teaching_request_detection(self):
        from mentor import is_teaching_request
        assert is_teaching_request("Amma explain async await")
        assert is_teaching_request("amma teach me about Redis")
        assert not is_teaching_request("open YouTube")

    def test_stuck_detector_not_stuck_initially(self):
        from mentor import StuckDetector
        sd = StuckDetector()
        assert not sd.is_stuck()

    def test_stuck_detector_detects(self):
        from mentor import StuckDetector
        sd = StuckDetector()
        # Signal 1: lots of deletes
        for _ in range(15):
            sd.record_edit(5, 20)
        # Signal 2: repeated searches
        for _ in range(5):
            sd.record_search("python async await")
        # Signal 3: tab switches
        sd.tab_switch_count = 15
        assert sd.is_stuck()

    def test_skill_gap_tracker(self):
        from mentor import SkillGapTracker
        tracker = SkillGapTracker()
        for _ in range(5):
            tracker.record_search("redis pub sub")
        gaps = tracker.get_skill_gaps()
        assert len(gaps) == 1
        assert gaps[0].count == 5

    def test_skill_gap_mark_addressed(self):
        from mentor import SkillGapTracker
        tracker = SkillGapTracker()
        for _ in range(4):
            tracker.record_search("fastapi middleware")
        tracker.mark_addressed("fastapi middleware")
        assert len(tracker.get_skill_gaps()) == 0

    def test_life_phase_student(self):
        from mentor import detect_life_phase
        assert detect_life_phase(in_school=True) == "STUDENT"

    def test_life_phase_senior(self):
        from mentor import detect_life_phase
        assert detect_life_phase(years_experience=10) == "SENIOR"


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5 — Social Layer
# ═══════════════════════════════════════════════════════════════════════════════

class TestSocial:
    def test_report_card_scoring(self):
        from social.network import WeeklyReportCard
        card = WeeklyReportCard(
            user_id="u1", week_start=datetime.now(timezone.utc),
            focus_time_pct=0.8, consistency_score=0.9,
            sleep_regularity=0.7, phone_discipline=0.8,
            amma_responsiveness=0.9, said_thank_you=True,
        )
        assert 70 <= card.raw_score <= 100

    def test_report_card_deductions(self):
        from social.network import WeeklyReportCard
        card = WeeklyReportCard(
            user_id="u1", week_start=datetime.now(timezone.utc),
            focus_time_pct=0.9, consistency_score=0.9,
            sleep_regularity=0.9, phone_discipline=0.9,
            amma_responsiveness=0.9, nuclear_events=2,
        )
        # 2 nuclear events = -40 points
        assert card.raw_score < 60

    def test_report_card_grade(self):
        from social.network import WeeklyReportCard
        card = WeeklyReportCard(
            user_id="u1", week_start=datetime.now(timezone.utc),
            focus_time_pct=1.0, consistency_score=1.0,
            sleep_regularity=1.0, phone_discipline=1.0,
            amma_responsiveness=1.0, said_thank_you=True,
        )
        assert card.grade in ("A+", "A")

    def test_council_verdict_generation(self):
        from social.council import AmmaCouncil
        council = AmmaCouncil()
        verdict = council.generate_verdict(95.0, "english", {"score": 95})
        assert len(verdict) > 0

    def test_council_percentile(self):
        from social.council import AmmaCouncil
        council = AmmaCouncil()
        pct = council.compute_percentile(80, [50, 60, 70, 80, 90])
        assert pct == 60.0  # 3 out of 5 below

    def test_receipt_generation(self):
        from social.receipts import generate_receipt
        receipt = generate_receipt("Chotu", "Week of Mar 3", 89, 260, 0, "pride")
        assert receipt.council_verdict == "Hall of Pride"
        assert "4 hrs" in receipt.best_streak


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5 — Parent Portal
# ═══════════════════════════════════════════════════════════════════════════════

class TestParentPortal:
    def test_sharing_config_defaults(self):
        from parent_portal import ParentSharingConfig
        config = ParentSharingConfig()
        assert config.share_weekly_score is True
        assert config.allow_whatsapp_share is False  # ALWAYS defaults OFF

    def test_voice_message_validation(self):
        from parent_portal import VoiceMessage
        valid = VoiceMessage(parent_id="p1", child_id="c1",
                             audio_path="/audio/msg.wav", duration_seconds=30)
        assert valid.is_valid
        too_long = VoiceMessage(parent_id="p1", child_id="c1",
                                audio_path="/audio/msg.wav", duration_seconds=90)
        assert not too_long.is_valid

    def test_shame_notification(self):
        from parent_portal import generate_shame_notification
        notif = generate_shame_notification("Chotu", 23)
        assert "Chotu" in notif
        assert "23/100" in notif

    def test_whatsapp_share_format(self):
        from parent_portal import generate_whatsapp_share
        msg = generate_whatsapp_share("Chotu", 91, "Hall of Pride", "Good week.")
        assert "🎉" in msg
        assert "91/100" in msg

    def test_parent_letter_validation(self):
        from parent_portal import ParentLetter
        letter = ParentLetter(parent_id="p1", child_id="c1",
                              content="Please be gentle with him this week.")
        assert letter.is_valid
        empty = ParentLetter(parent_id="p1", child_id="c1", content="")
        assert not empty.is_valid


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5 — Emotional Intelligence
# ═══════════════════════════════════════════════════════════════════════════════

class TestEmotional:
    def test_distress_level_normal(self):
        from emotional import EmotionalStateMonitor
        monitor = EmotionalStateMonitor()
        assert monitor.get_distress_level() == "NORMAL"

    def test_distress_level_watchful(self):
        from emotional import EmotionalStateMonitor
        monitor = EmotionalStateMonitor()
        monitor.add_signal("sad_music")
        assert monitor.get_distress_level() == "WATCHFUL"

    def test_distress_level_support(self):
        from emotional import EmotionalStateMonitor
        monitor = EmotionalStateMonitor()
        monitor.add_signal("sleep_disrupted")
        monitor.add_signal("output_dropped")
        assert monitor.get_distress_level() == "SUPPORT"

    def test_distress_level_crisis_verbal(self):
        from emotional import EmotionalStateMonitor
        monitor = EmotionalStateMonitor()
        monitor.add_signal("verbal_distress")
        assert monitor.get_distress_level() == "CRISIS"

    def test_distress_level_crisis_count(self):
        from emotional import EmotionalStateMonitor
        monitor = EmotionalStateMonitor()
        for sig in ["sleep_disrupted", "output_dropped", "unusual_hours", "eating_disrupted"]:
            monitor.add_signal(sig)
        assert monitor.get_distress_level() == "CRISIS"

    def test_burnout_not_at_risk(self):
        from emotional import BurnoutIndicators
        bi = BurnoutIndicators()
        assert not bi.is_at_risk()

    def test_burnout_at_risk(self):
        from emotional import BurnoutIndicators
        bi = BurnoutIndicators(
            avg_daily_hours=12, consecutive_weekend_work=4,
            sleep_debt_hours=8,
        )
        assert bi.is_at_risk()

    def test_wellbeing_score(self):
        from emotional import WellbeingScore
        ws = WellbeingScore(
            sleep_regularity=0.8, social_frequency=0.7,
            physical_activity=0.6, eating_regularity=0.7,
            emotional_absence=0.9, self_reported_mood=0.8,
        )
        assert 60 <= ws.total <= 100
        assert ws.status in ("GOOD", "EXCELLENT")

    def test_wellbeing_critical(self):
        from emotional import WellbeingScore
        ws = WellbeingScore()  # All zeros
        assert ws.total == 0
        assert ws.status == "CRITICAL"

    def test_cinematic_moments(self):
        from emotional import get_cinematic_moment
        moment = get_cinematic_moment("job_offer")
        assert len(moment) >= 2
        assert "BETA" in moment[0]


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6 — Gamification
# ═══════════════════════════════════════════════════════════════════════════════

class TestGamification:
    def test_xp_level_calculation(self):
        from gamification import calculate_level
        assert calculate_level(0) == 1
        assert calculate_level(1000) == 5
        assert calculate_level(7000) == 15
        assert calculate_level(400000) == 50

    def test_get_title(self):
        from gamification import get_title
        assert get_title(1) == "The Beginner"
        assert get_title(20) == "Amma's Pride"
        assert get_title(50) == "Nanna Maga / Nanna Magale"

    def test_streak_valid_day(self):
        from gamification import StreakState
        s = StreakState()
        s.record_valid_day(date(2026, 3, 8))
        assert s.daily_work == 1
        s.record_valid_day(date(2026, 3, 9))
        assert s.daily_work == 2

    def test_streak_missed_day_with_grace(self):
        from gamification import StreakState
        s = StreakState()
        s.record_valid_day(date(2026, 3, 8))
        s.record_valid_day(date(2026, 3, 10))  # Missed Mar 9
        assert s.daily_work == 2
        assert s.grace_tokens_remaining == 1

    def test_streak_missed_day_no_grace(self):
        from gamification import StreakState
        s = StreakState(grace_tokens_remaining=0)
        s.record_valid_day(date(2026, 3, 8))
        s.record_valid_day(date(2026, 3, 10))  # Missed, no tokens
        assert s.daily_work == 1  # Reset

    def test_user_achievements_xp(self):
        from gamification import UserAchievements
        ua = UserAchievements(user_id="u1")
        ua.award_xp("valid_streak_day")
        assert ua.current_xp == 50

    def test_user_achievements_level_up(self):
        from gamification import UserAchievements
        ua = UserAchievements(user_id="u1")
        new_level = ua.award_xp("valid_streak_day", 1000)
        assert new_level == 5
        assert ua.current_title == "Showing Up"

    def test_badge_award(self):
        from gamification import UserAchievements
        ua = UserAchievements(user_id="u1")
        badge = ua.award_badge("first_reset")
        assert badge is not None
        assert "first_reset" in ua.badges

    def test_badge_no_duplicate(self):
        from gamification import UserAchievements
        ua = UserAchievements(user_id="u1")
        ua.award_badge("first_reset")
        second = ua.award_badge("first_reset")
        assert second is None

    def test_badge_optimization_detection(self):
        from gamification import detect_badge_optimization
        # User always stops at exactly 120 min
        sessions = [120, 121, 119, 120, 120, 120, 122, 120, 119, 120]
        assert detect_badge_optimization(sessions)

    def test_no_badge_optimization(self):
        from gamification import detect_badge_optimization
        sessions = [45, 90, 150, 200, 60, 180, 75, 110, 240, 30]
        assert not detect_badge_optimization(sessions)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6 — Smriti Memory
# ═══════════════════════════════════════════════════════════════════════════════

class TestSmriti:
    def test_significance_scoring(self):
        from smriti import compute_significance
        score = compute_significance({"type": "job_offer"})
        assert score == 1.0

    def test_significance_with_modifiers(self):
        from smriti import compute_significance
        score = compute_significance({
            "type": "daily_session",
            "emotional_intensity": "high",
            "is_first_occurrence": True,
        })
        assert score == pytest.approx(0.55)  # 0.3 + 0.15 + 0.10

    def test_memory_store_ingest_retrieve(self):
        from smriti import SmritiStore, MemoryRecord
        store = SmritiStore()
        mem = MemoryRecord(
            memory_id="m1", user_id="u1",
            occurred_at=datetime.now(timezone.utc),
            category="life_milestone", content="Got the job offer!",
            significance=1.0,
        )
        store.ingest(mem)
        results = store.retrieve_relevant("u1")
        assert len(results) == 1
        assert results[0].content == "Got the job offer!"

    def test_memory_store_min_significance_filter(self):
        from smriti import SmritiStore, MemoryRecord
        store = SmritiStore()
        store.ingest(MemoryRecord(
            memory_id="m1", user_id="u1",
            occurred_at=datetime.now(timezone.utc),
            category="session", content="Regular session",
            significance=0.3,
        ))
        results = store.retrieve_relevant("u1", min_significance=0.6)
        assert len(results) == 0

    def test_memory_delete(self):
        from smriti import SmritiStore, MemoryRecord
        store = SmritiStore()
        store.ingest(MemoryRecord(
            memory_id="m1", user_id="u1",
            occurred_at=datetime.now(timezone.utc),
            category="test", content="Test memory",
        ))
        assert store.delete_memory("u1", "m1")
        assert len(store.retrieve_relevant("u1", min_significance=0.0)) == 0

    def test_memory_delete_all(self):
        from smriti import SmritiStore, MemoryRecord
        store = SmritiStore()
        for i in range(5):
            store.ingest(MemoryRecord(
                memory_id=f"m{i}", user_id="u1",
                occurred_at=datetime.now(timezone.utc),
                category="test", content=f"Memory {i}",
            ))
        count = store.delete_all("u1")
        assert count == 5

    def test_memory_export(self):
        from smriti import SmritiStore, MemoryRecord
        store = SmritiStore()
        store.ingest(MemoryRecord(
            memory_id="m1", user_id="u1",
            occurred_at=datetime.now(timezone.utc),
            category="test", content="Exportable",
        ))
        exported = store.export_all("u1")
        assert len(exported) == 1
        assert exported[0]["content"] == "Exportable"

    def test_memory_context_block(self):
        from smriti import MemoryRecord, build_memory_context_block
        mems = [MemoryRecord(
            memory_id="m1", user_id="u1",
            occurred_at=datetime(2025, 10, 15, tzinfo=timezone.utc),
            category="milestone", content="First 100-day streak",
        )]
        block = build_memory_context_block(mems)
        assert "Oct 2025" in block
        assert "100-day streak" in block

    def test_excuse_archive(self):
        from smriti import ExcuseArchive, ExcuseRecord
        archive = ExcuseArchive()
        for i in range(5):
            archive.record(ExcuseRecord(
                excuse_id=f"e{i}", user_id="u1",
                occurred_at=datetime.now(timezone.utc),
                excuse_type="night_owl", exact_words="I work better at night",
                context="YouTube at 11pm", claimed_validity="night productivity",
                validated=(i < 1),
            ))
        history = archive.get_history("u1", "night_owl")
        assert history["count"] == 5
        assert history["validation_rate"] == 0.2


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6 — Deployment & Config
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeployment:
    def test_full_config_defaults(self):
        from deployment import AmmaFullConfig
        config = AmmaFullConfig()
        assert config.personality.strictness == 8
        assert config.thresholds.level_1_minutes == 45
        assert config.audio.voice == "Aoede"

    def test_onboarding_state(self):
        from deployment import OnboardingState
        state = OnboardingState(user_id="u1")
        assert state.step_name == "install_client"
        state.advance()
        assert state.step_name == "first_words"
        for _ in range(10):
            state.advance()
        assert state.completed

    def test_first_session_adjustments(self):
        from deployment import AmmaFullConfig, first_session_adjustments
        config = AmmaFullConfig()
        adj = first_session_adjustments(config)
        assert adj["strictness_cap"] <= 6
        assert adj["extra_patience_minutes"] == 15

    def test_structured_log_event(self):
        from deployment import AmmaLogEvent
        evt = AmmaLogEvent(
            user_id="u1", session_id="s1",
            event_type="CLASSIFICATION", classification="WORK",
            confidence=0.95, latency_ms=350,
        )
        j = evt.to_json()
        assert '"WORK"' in j
        assert '"0.95"' not in j  # Should be number, not string

    def test_fallback_classify_window_title(self):
        from deployment import fallback_classify_window_title
        assert fallback_classify_window_title("VS Code - main.py") == "WORK"
        assert fallback_classify_window_title("Netflix - Stranger Things") == "TIMEPASS"
        assert fallback_classify_window_title("Some random window") == "GREY"

    def test_fallback_classify_time(self):
        from deployment import fallback_classify_time
        assert fallback_classify_time(14) == "WORK"
        assert fallback_classify_time(23) == "GREY"
