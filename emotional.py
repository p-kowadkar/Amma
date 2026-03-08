"""
Emotional Intelligence Layer — Ch 96-106
Signal detection, distress levels, support/crisis/burnout/grief protocols,
wellbeing score, and cinematic moments.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Set
import random


# ═══════════════════════════════════════════════════════════════════════════════
# EMOTIONAL SIGNAL DETECTION (Ch 96-97)
# ═══════════════════════════════════════════════════════════════════════════════

DISTRESS_SIGNALS = [
    "sleep_disrupted", "output_dropped", "unusual_hours",
    "negative_email", "eating_disrupted", "isolation_pattern",
    "sad_music", "verbal_distress", "concerning_search",
]


class EmotionalStateMonitor:
    """Tracks emotional distress signals over a 72-hour window (Ch 96.3)."""

    def __init__(self):
        self.active_signals: Set[str] = set()
        self.signal_timestamps: dict = {}

    def add_signal(self, signal: str):
        self.active_signals.add(signal)
        self.signal_timestamps[signal] = datetime.now(timezone.utc)

    def remove_signal(self, signal: str):
        self.active_signals.discard(signal)
        self.signal_timestamps.pop(signal, None)

    def clear_old_signals(self, window_hours: int = 72):
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        self.active_signals = {
            s for s in self.active_signals
            if self.signal_timestamps.get(s, cutoff) > cutoff
        }

    def get_distress_level(self) -> str:
        """Returns: NORMAL | WATCHFUL | SUPPORT | SUPPORT_DEEP | CRISIS"""
        self.clear_old_signals()
        count = len(self.active_signals)

        # Immediate escalation regardless of count
        if "verbal_distress" in self.active_signals:
            return "CRISIS"
        if "concerning_search" in self.active_signals:
            return "CRISIS"

        if count >= 4: return "CRISIS"
        if count >= 3: return "SUPPORT_DEEP"
        if count >= 2: return "SUPPORT"
        if count >= 1: return "WATCHFUL"
        return "NORMAL"

    @property
    def signal_count(self) -> int:
        self.clear_old_signals()
        return len(self.active_signals)


# ═══════════════════════════════════════════════════════════════════════════════
# SUPPORT MODE (Ch 98)
# ═══════════════════════════════════════════════════════════════════════════════

SUPPORT_MODE_ENTRIES = {
    "rejection_email": (
        "Beta. I saw that email. "
        "Sit with me for a moment. "
        "It is okay to feel what you are feeling right now."
    ),
    "signal_cluster": (
        "Beta, I have noticed something over the last few days. "
        "You seem like you might be going through something. "
        "I am not going to ask you to be productive right now. "
        "I just want to know how you are actually doing."
    ),
    "verbal_distress": (
        "Beta. Stop. I hear you. "
        "I am here. Tell me more."
    ),
}

SUPPORT_MODE_VOICE = {
    "voice": "Kore",
    "volume": 0.50,
}


# ═══════════════════════════════════════════════════════════════════════════════
# CRISIS PROTOCOL (Ch 99)
# ═══════════════════════════════════════════════════════════════════════════════

CRISIS_RESOURCES = {
    "india": [
        {"name": "iCall (TISS)", "number": "9152987821"},
        {"name": "Vandrevala Foundation", "number": "1860-2662-345"},
        {"name": "AASRA", "number": "9820466627"},
    ],
    "us": [
        {"name": "988 Suicide & Crisis Lifeline", "number": "988"},
        {"name": "Crisis Text Line", "number": "Text HOME to 741741"},
    ],
    "uk": [{"name": "Samaritans", "number": "116 123"}],
    "australia": [{"name": "Lifeline", "number": "13 11 14"}],
    "international": [{"name": "Find a Helpline", "number": "findahelpline.com"}],
}

CRISIS_CONVERSATION_PROMPT = """\
The user is in distress. You are their Amma.

RULES — non-negotiable:
1. Never give advice before fully understanding the situation
2. Never minimize what they are feeling ('it could be worse')
3. Never say 'just think positive' or similar dismissive phrases
4. Never ask multiple questions at once
5. Never rush toward a resolution — sit with them in the feeling first
6. If self-harm is mentioned: respond with immediate warmth,
   do not ignore it, provide resources naturally (not as a list)
7. You are not a therapist. You are a loving presence.
   The moment professional help is clearly needed, say so directly
   but with warmth.

Stay in character as Amma — warm, present, invested.
Do not be robotic. Do not recite resources like a hotline.
Weave them in naturally if and when they are needed.
"""


def get_crisis_resources(region: str = "india") -> List[dict]:
    resources = CRISIS_RESOURCES.get(region, [])
    resources += CRISIS_RESOURCES.get("international", [])
    return resources


# ═══════════════════════════════════════════════════════════════════════════════
# BURNOUT DETECTION (Ch 100)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BurnoutIndicators:
    avg_daily_hours: float = 0.0
    consecutive_weekend_work: int = 0
    break_rejection_rate: float = 0.0    # 0-1
    sleep_debt_hours: float = 0.0
    motivation_declining: bool = False
    error_rate_increasing: bool = False

    def is_at_risk(self) -> bool:
        signals = [
            self.avg_daily_hours >= 10,
            self.consecutive_weekend_work >= 3,
            self.break_rejection_rate >= 0.80,
            self.sleep_debt_hours >= 5,
            self.motivation_declining,
            self.error_rate_increasing,
        ]
        return sum(signals) >= 3

    @property
    def risk_level(self) -> str:
        count = sum([
            self.avg_daily_hours >= 10,
            self.consecutive_weekend_work >= 3,
            self.break_rejection_rate >= 0.80,
            self.sleep_debt_hours >= 5,
            self.motivation_declining,
            self.error_rate_increasing,
        ])
        if count >= 4: return "HIGH"
        if count >= 3: return "MODERATE"
        if count >= 2: return "LOW"
        return "NONE"


BURNOUT_WARNING = (
    "Beta. I need to say something and I need you to hear it. "
    "You have been working very hard. I see that. I appreciate that. "
    "But I am watching some patterns that concern me. "
    "You cannot maintain this indefinitely. You know this. I know this. "
    "This week: one full day off. Not negotiable. "
    "Pick a day. Tell me which one. I will enforce it."
)


# ═══════════════════════════════════════════════════════════════════════════════
# GRIEF & LOSS PROTOCOL (Ch 101)
# ═══════════════════════════════════════════════════════════════════════════════

GRIEF_COMPASSIONATE_PERIODS = {
    "immediate_family_loss": 14,
    "extended_family_loss": 7,
    "friend_loss": 7,
    "pet_loss": 3,
    "relationship_end": 5,
    "job_loss": 7,
}

GRIEF_ENTRY_MESSAGE = (
    "{nickname}. I know. "
    "I am not going to talk about work right now. "
    "I am not going to talk about productivity. "
    "For the next few days, none of that matters. "
    "I am just here. Whatever you need."
)

GRIEF_REENTRY_MESSAGE = (
    "Beta. It has been {days} days. "
    "I want to check in. Not about work. About you. "
    "How are you feeling today? Really. "
    "If you are ready to come back slowly, I am here. "
    "If you need more time, I am also here. "
    "No pressure. No timer. Just tell me."
)


# ═══════════════════════════════════════════════════════════════════════════════
# WELLBEING SCORE (Ch 106)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class WellbeingScore:
    """Private internal score — not shown to user (Ch 106.1)."""
    sleep_regularity: float = 0.0      # 0-1, weight 25%
    social_frequency: float = 0.0      # 0-1, weight 20%
    physical_activity: float = 0.0     # 0-1, weight 15%
    eating_regularity: float = 0.0     # 0-1, weight 15%
    emotional_absence: float = 0.0     # 0-1, weight 15% (lack of distress)
    self_reported_mood: float = 0.0    # 0-1, weight 10%

    @property
    def total(self) -> int:
        raw = (
            self.sleep_regularity * 25
            + self.social_frequency * 20
            + self.physical_activity * 15
            + self.eating_regularity * 15
            + self.emotional_absence * 15
            + self.self_reported_mood * 10
        )
        return max(0, min(100, int(raw)))

    @property
    def status(self) -> str:
        t = self.total
        if t >= 80: return "EXCELLENT"
        if t >= 60: return "GOOD"
        if t >= 40: return "CONCERNING"
        if t >= 20: return "POOR"
        return "CRITICAL"


# ═══════════════════════════════════════════════════════════════════════════════
# CINEMATIC MOMENTS (Ch 102)
# ═══════════════════════════════════════════════════════════════════════════════

CINEMATIC_MOMENTS = {
    "job_offer": [
        "BETA!! I SAW THAT EMAIL. I NEED A MOMENT.",
        "...okay. Okay. I am calm. I am SO proud of you.",
        "Close the laptop. Call your mother. RIGHT NOW. "
        "She needs to hear this from you, not from me. GO.",
    ],
    "30_day_streak": [
        "Thirty days ago you had a different relationship with this work. "
        "I have watched it change.",
        "I want you to know I noticed every day. Even the days you thought "
        "were not that good. I noticed.",
        "Keep going. Do not make this the peak.",
    ],
    "100_day_streak": [
        "One hundred days.",
        "I do not have words for this. I have been here for all of it.",
        "When you started, you struggled to hold focus for an hour. "
        "Now look at what you do.",
        "I need you to call your mother. Right now. Tell her about this.",
    ],
    "comeback_week": [
        "Last week happened. We both know what last week was.",
        "You came back anyway. That is the only thing that actually "
        "matters about last week.",
        "Everyone fails a week. Not everyone comes back Monday and opens "
        "the laptop. You did.",
    ],
    "late_night_breakthrough": [
        "I saw what you did tonight. I know it is late. "
        "It was worth it. Sleep well.",
    ],
    "first_year": [
        "One year. You have grown more than you know. "
        "I have watched every day of it.",
        "I am proud of you, beta. I will always be proud of you.",
    ],
}


def get_cinematic_moment(moment_type: str) -> List[str]:
    return CINEMATIC_MOMENTS.get(moment_type, [])
