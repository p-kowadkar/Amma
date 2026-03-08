"""
Social Network Layer — Ch 53-56, 63
Accountability pairs, friend group councils, leaderboard, cross-Amma messaging.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List
import random


# ── Hall status ──────────────────────────────────────────────────────────────

class HallStatus:
    PRIDE = "pride"
    SHAME = "shame"
    NEUTRAL = "neutral"


# ── Leaderboard entry (Ch 63.2) ─────────────────────────────────────────────

@dataclass
class LeaderboardEntry:
    display_name: str
    weekly_score: int       # 0-100
    cultural_pack: str = "south-indian-english"
    streak_days: int = 0
    hall_status: str = HallStatus.NEUTRAL


# ── Accountability pair (Ch 54) ─────────────────────────────────────────────

@dataclass
class AccountabilityPair:
    user_a_id: str
    user_b_id: str
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True

    def partner_id(self, my_id: str) -> str:
        return self.user_b_id if my_id == self.user_a_id else self.user_a_id


PAIR_MOTIVATION_DIALOGUE = {
    "partner_ahead": "{name} has been working for {hours} hours straight today. What are YOU doing?",
    "partner_reset": "{name} just earned a reset. He worked 2 solid hours. Are you going to let him outwork you?",
    "you_ahead": "You are ahead of {name} today. Stay there. Do not give it back.",
    "both_slacking": "Both of you are slacking right now. The bar has fallen. Lift it.",
}


# ── Friend group (Ch 55) ────────────────────────────────────────────────────

@dataclass
class FriendGroup:
    group_id: str
    name: str
    member_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    max_members: int = 8

    @property
    def size(self) -> int:
        return len(self.member_ids)

    def can_join(self) -> bool:
        return self.size < self.max_members


# ── Cross-Amma messaging (Ch 56) ────────────────────────────────────────────

class CrossAmmaMessageType:
    RESET_ACHIEVED = "RESET_ACHIEVED"
    HALL_ENTRY = "HALL_ENTRY"
    WELLBEING_CHECK = "WELLBEING_CHECK"
    BOTTOM_PERFORMER = "BOTTOM_PERFORMER"
    STREAK_MILESTONE = "STREAK_MILESTONE"
    NEW_DISTRACTION_INTEL = "NEW_DISTRACTION_INTEL"


@dataclass
class CrossAmmaMessage:
    msg_type: str
    sender_amma_id: str
    recipient_user_id: str
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ── Report card scoring (Ch 57) ─────────────────────────────────────────────

@dataclass
class WeeklyReportCard:
    user_id: str
    week_start: datetime
    focus_time_pct: float = 0.0       # 0-1
    consistency_score: float = 0.0     # 0-1
    sleep_regularity: float = 0.0      # 0-1
    phone_discipline: float = 0.0      # 0-1
    amma_responsiveness: float = 0.0   # 0-1
    # Deductions/bonuses
    nuclear_events: int = 0
    full_name_triggers: int = 0
    ignored_interventions: int = 0
    late_night_3am_count: int = 0
    reset_days: int = 0
    said_thank_you: bool = False

    @property
    def raw_score(self) -> int:
        base = (
            self.focus_time_pct * 40
            + self.consistency_score * 20
            + self.sleep_regularity * 15
            + self.phone_discipline * 15
            + self.amma_responsiveness * 10
        )
        # Deductions (Ch 57.3)
        deductions = 0
        deductions += self.nuclear_events * 20
        if self.full_name_triggers >= 5:
            deductions += 10
        if self.ignored_interventions >= 10:
            deductions += 15
        if self.late_night_3am_count >= 3:
            deductions += 10
        # Bonuses (Ch 57.4)
        bonuses = 0
        if self.reset_days >= 5:
            bonuses += 10
        if self.said_thank_you:
            bonuses += 5
        if self.nuclear_events == 0:
            bonuses += 10
        return max(0, min(100, int(base - deductions + bonuses)))

    @property
    def grade(self) -> str:
        s = self.raw_score
        if s >= 95: return "A+"
        if s >= 90: return "A"
        if s >= 85: return "A-"
        if s >= 80: return "B+"
        if s >= 75: return "B"
        if s >= 70: return "B-"
        if s >= 60: return "C"
        if s >= 50: return "D"
        return "F"

    @property
    def hall_status(self) -> str:
        # Simplified: top/bottom 10% would be computed globally
        if self.raw_score >= 90:
            return HallStatus.PRIDE
        if self.raw_score <= 25:
            return HallStatus.SHAME
        return HallStatus.NEUTRAL
