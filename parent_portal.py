"""
I'm an Amma — Parent Portal — Ch 64-72
Parent dashboard data models, voice message protocol, privacy controls,
family WhatsApp share, and the parent council view.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List
import random


# ── Parent sharing config (Ch 71.3) ─────────────────────────────────────────

@dataclass
class ParentSharingConfig:
    """Child controls what parent can see — child ALWAYS has final say."""
    share_weekly_score: bool = True
    share_hall_status: bool = True
    share_trend: bool = True
    share_realtime_status: bool = True
    share_sleep_indicator: bool = True
    share_eating_indicator: bool = False
    allow_voice_messages: bool = True
    allow_strict_mode_request: bool = True
    allow_event_injection: bool = True
    allow_whatsapp_share: bool = False   # ALWAYS defaults OFF
    disable_parent_portal: bool = False  # One button to pause all sharing


# ── Parent dashboard data (Ch 65) ───────────────────────────────────────────

class ChildStatus:
    WORKING = "working"        # 🟢
    RESTING = "resting"        # 🔵
    AWAY = "away"              # ⚪
    LATE_NIGHT = "late_night"  # 🌙
    NOT_GREAT = "not_great"    # 🟡


@dataclass
class ParentDashboard:
    child_name: str
    status: str = ChildStatus.AWAY
    weekly_score: int = 0
    focus_trend: str = "stable"      # improving | declining | stable
    sleep_indicator: str = "unknown"  # adequate | poor | unknown
    eating_indicator: str = "unknown"
    hall_status: str = "neutral"
    last_active: Optional[datetime] = None
    amma_weekly_note: str = ""

    @property
    def status_emoji(self) -> str:
        return {
            ChildStatus.WORKING: "🟢",
            ChildStatus.RESTING: "🔵",
            ChildStatus.AWAY: "⚪",
            ChildStatus.LATE_NIGHT: "🌙",
            ChildStatus.NOT_GREAT: "🟡",
        }.get(self.status, "⚪")


# ── Voice message protocol (Ch 66) ──────────────────────────────────────────

class DeliveryTrigger:
    ANY_TIME = "any_time"
    DURING_WORK = "during_work"
    IF_SLACKING = "if_slacking"          # Level 2+
    BEFORE_EVENT = "before_event"
    SPECIFIC_TIME = "specific_time"


@dataclass
class VoiceMessage:
    parent_id: str
    child_id: str
    audio_path: str               # Cloud storage path
    duration_seconds: float = 0.0
    delivery_trigger: str = DeliveryTrigger.ANY_TIME
    delivered: bool = False
    delivered_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_valid(self) -> bool:
        return 0 < self.duration_seconds <= 60


VOICE_MESSAGE_FOLLOW_UPS = [
    "She loves you very much, beta. Do not waste that.",
    "Your mother took time to send that. Make it worth something.",
    "I thought you should hear that. Now get back to work.",
    "...she is proud of you. Even when I am not. Remember that.",
]


# ── Parent event injection (Ch 67.4) ────────────────────────────────────────

@dataclass
class ParentEvent:
    event_type: str          # INTERVIEW | EXAM | DEADLINE | BIRTHDAY | CUSTOM
    date: str                # ISO date
    description: str
    strictness_boost: int = 0  # 0-3
    parent_note: str = ""


# ── Extra strict mode (Ch 67.5) ─────────────────────────────────────────────

@dataclass
class StrictModeRequest:
    enabled: bool = False
    duration_days: int = 7
    threshold_multiplier: float = 0.70  # 45 min → 31 min
    parent_note: str = ""


# ── Hall of Shame parent notification (Ch 69) ───────────────────────────────

HALL_OF_SHAME_PARENT_TEMPLATE = """\
Dear Amma-ji,

This week was a difficult one for {name}.
He scored {score}/100 — his lowest score in {weeks_since_low} weeks.
The Amma has been working with him.

You do not need to do anything specific.
But if you were thinking of calling this weekend,
this would be a good weekend for it.

He is okay. He just needs to hear from you.

— The Council
(Delivered via I'm an Amma)
"""


def generate_shame_notification(name: str, score: int, weeks_since_low: int = 4) -> str:
    return HALL_OF_SHAME_PARENT_TEMPLATE.format(
        name=name, score=score, weeks_since_low=weeks_since_low,
    )


# ── WhatsApp share format (Ch 70) ───────────────────────────────────────────

def generate_whatsapp_share(name: str, score: int, verdict: str, note: str) -> str:
    emoji = "🎉" if verdict == "Hall of Pride" else "😤"
    return (
        f"Beta log — {name} ka weekly update {emoji}\n\n"
        f"Amma app report:\n"
        f"- Score this week: {score}/100\n"
        f"- Council verdict: {verdict}\n"
        f"- Amma's note: \"{note}\"\n\n"
        f"— Shared via I'm an Amma 🇮🇳"
    )


# ── Monthly parent letter (Ch 72.3) ─────────────────────────────────────────

@dataclass
class ParentLetter:
    parent_id: str
    child_id: str
    content: str           # Up to 200 words
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_valid(self) -> bool:
        return 0 < len(self.content.split()) <= 200
