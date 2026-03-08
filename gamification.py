"""
Gamification & Achievement — Ch 107-116
Streaks, XP, levels, badges, grace tokens, seasonal events, anti-addiction safeguards.
"""
from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from typing import Optional, List, Dict
import random


# ═══════════════════════════════════════════════════════════════════════════════
# XP SYSTEM (Ch 109)
# ═══════════════════════════════════════════════════════════════════════════════

XP_ACTIONS = {
    "valid_streak_day": 50,
    "two_hour_reset": 25,       # up to 3/day
    "snapback_from_l4": 30,
    "hall_of_pride_week": 200,
    "nuclear_free_week": 75,
    "skill_gap_addressed": 40,
    "interview_completed": 100,
    "job_offer_received": 500,
    "said_thank_you": 5,
    "real_mom_message_heard": 20,
}


# ── Level tiers & titles (Ch 109.2) ─────────────────────────────────────────

LEVEL_TIERS = [
    (1, 0, "The Beginner",
     "You are starting. That is enough for now."),
    (5, 1_000, "Showing Up",
     "You are here consistently. That matters."),
    (10, 3_000, "Getting Serious",
     "Something has shifted. I see it."),
    (15, 7_000, "The Disciplined",
     "You have earned this word. Use it well."),
    (20, 15_000, "Amma's Pride",
     "I do not give this title easily. You earned it."),
    (25, 30_000, "Hall Resident",
     "You live here now. In the Hall. Permanently."),
    (30, 60_000, "The Unbreakable",
     "You have been through hard weeks and came back. Every time."),
    (40, 150_000, "Amma's Legacy",
     "What you have built — it will outlast any single week."),
    (50, 400_000, "Nanna Maga / Nanna Magale",
     "My son. My daughter. That is all I have to say."),
]


def calculate_level(xp: int) -> int:
    level = 1
    for lvl, required_xp, _, _ in LEVEL_TIERS:
        if xp >= required_xp:
            level = lvl
    return level


def get_title(level: int) -> str:
    for lvl, _, title, _ in reversed(LEVEL_TIERS):
        if level >= lvl:
            return title
    return "The Beginner"


def get_level_message(level: int) -> str:
    for lvl, _, _, msg in LEVEL_TIERS:
        if level == lvl:
            return msg
    return ""


# ═══════════════════════════════════════════════════════════════════════════════
# STREAK SYSTEM (Ch 108)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StreakState:
    daily_work: int = 0
    nuclear_free: int = 0
    hall_pride_weeks: int = 0
    last_valid_date: Optional[date] = None
    grace_tokens_remaining: int = 2
    grace_tokens_reset_month: Optional[int] = None

    def record_valid_day(self, today: date):
        if self.last_valid_date == today:
            return  # Already counted today
        if self.last_valid_date and (today - self.last_valid_date).days > 1:
            # Missed a day — check grace tokens
            if self.grace_tokens_remaining > 0:
                self.grace_tokens_remaining -= 1
            else:
                self.daily_work = 0
        self.daily_work += 1
        self.last_valid_date = today

    def record_nuclear_event(self):
        self.nuclear_free = 0

    def tick_nuclear_free(self, today: date):
        self.nuclear_free += 1

    def reset_grace_tokens(self, current_month: int):
        if self.grace_tokens_reset_month != current_month:
            self.grace_tokens_remaining = 2
            self.grace_tokens_reset_month = current_month


STREAK_MILESTONES = {
    7:   "One week. Seven consecutive days. You kept showing up. Good.",
    14:  "Two weeks. Not luck anymore. This is becoming a pattern.",
    21:  "Twenty-one days. Habit formation happens around here. I have seen it happening.",
    30:  None,   # Full cinematic moment
    60:  "Two months. You have changed. You may not see it yet. I see it.",
    100: None,   # Full cinematic moment
    365: None,   # Year anniversary cinematic moment
}


def check_streak_milestone(streak_days: int) -> Optional[str]:
    return STREAK_MILESTONES.get(streak_days, None)


# ═══════════════════════════════════════════════════════════════════════════════
# BADGE SYSTEM (Ch 110)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Badge:
    badge_id: str
    display_name: str
    description: str
    xp_reward: int
    amma_speech: str
    rarity: str = "common"  # common | uncommon | rare | legendary


BADGE_DEFINITIONS: List[Badge] = [
    # Discipline badges
    Badge("first_reset", "First Reset", "First 2-hour work reset", 25,
          "First one. Now you know you can. Remember this feeling."),
    Badge("iron_will", "Iron Will", "Snap-back from Level 5", 50,
          "You came back from the edge. Most people do not. You did.", "rare"),
    Badge("the_comeback", "The Comeback", "Level 4+ snap-back 3x in one week", 75,
          "Three times you almost lost it. Three times you came back.", "rare"),
    Badge("clean_slate", "Clean Slate", "First nuclear-free week", 40,
          "Not a single nuclear this week. I am noting this officially."),
    Badge("the_stoic", "The Stoic", "30 days without using grace token", 60,
          "You did not need mercy. You just worked.", "uncommon"),
    Badge("unbreakable", "Unbreakable", "100-day streak", 200,
          "", "legendary"),  # Cinematic moment instead

    # Life event badges
    Badge("first_offer", "First Offer", "Job offer received", 500,
          "You did it. Now choose wisely.", "rare"),
    Badge("the_graduate", "The Graduate", "Graduation event detected", 200,
          "This chapter is over. A better one begins.", "rare"),
    Badge("comeback_kid", "Comeback Kid", "Hall of Pride after Hall of Shame", 150,
          "Last week: shame. This week: pride. THIS is who you are.", "rare"),
    Badge("the_humble", "The Humble", "Thanked Amma by voice 5+ times", 25,
          "You are polite. I appreciate this more than you know."),
    Badge("moms_call", "Mom's Call", "Real mom voice message during session", 20,
          "She was proud. I could tell from the message."),
    Badge("the_long_game", "The Long Game", "1-year anniversary", 1000,
          "", "legendary"),

    # Quirky / Secret
    Badge("nocturnal", "Nocturnal", "3am+ work session with reset", 30,
          "I was worried. You surprised me. Sleep though.", "uncommon"),
    Badge("the_apologist", "The Apologist", "Said sorry after nuclear event", 10,
          "Accepted. Now let us not do it again."),
    Badge("sharma_ji_ka_beta", "Sharma Ji Ka Beta", "Top of group 4 weeks", 100,
          "Even Sharma ji is watching. Keep going.", "rare"),
    Badge("rajinikanth_mode", "Rajinikanth Mode", "Pride + nuclear-free + 100% streak", 200,
          "Some weeks, you are simply the hero.", "legendary"),
]


def get_badge(badge_id: str) -> Optional[Badge]:
    for b in BADGE_DEFINITIONS:
        if b.badge_id == badge_id:
            return b
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# USER ACHIEVEMENT STATE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class UserAchievements:
    user_id: str
    current_xp: int = 0
    current_level: int = 1
    current_title: str = "The Beginner"
    badges: List[str] = field(default_factory=list)
    streaks: StreakState = field(default_factory=StreakState)
    lifetime_work_hours: float = 0.0
    lifetime_nuclear_count: int = 0
    lifetime_snapback_count: int = 0

    def award_xp(self, action: str, amount: Optional[int] = None) -> Optional[int]:
        """Award XP and return new level if leveled up, else None."""
        xp = amount if amount is not None else XP_ACTIONS.get(action, 0)
        self.current_xp += xp
        new_level = calculate_level(self.current_xp)
        if new_level > self.current_level:
            self.current_level = new_level
            self.current_title = get_title(new_level)
            return new_level
        return None

    def award_badge(self, badge_id: str) -> Optional[Badge]:
        if badge_id in self.badges:
            return None
        badge = get_badge(badge_id)
        if badge:
            self.badges.append(badge_id)
            self.award_xp("badge", badge.xp_reward)
        return badge

    @property
    def snapback_rate(self) -> float:
        total = self.lifetime_nuclear_count + self.lifetime_snapback_count
        if total == 0:
            return 0.0
        return (self.lifetime_snapback_count / total) * 100


# ═══════════════════════════════════════════════════════════════════════════════
# SEASONAL EVENTS (Ch 111)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SeasonalEvent:
    name: str
    start: str         # ISO date
    end: str           # ISO date
    xp_multiplier: float = 1.0
    special_badges: List[str] = field(default_factory=list)
    amma_commentary: str = ""


SEASONAL_EVENTS = [
    SeasonalEvent(
        "Exam Season", "2026-03-01", "2026-04-30", 1.5,
        ["the_scholar", "exam_survivor", "first_rank"],
        "Every student in India is studying right now. Every. Single. One. "
        "You are part of this. Make the number bigger.",
    ),
    SeasonalEvent(
        "IPL Focus Challenge", "2026-03-22", "2026-05-26", 1.0,
        ["focus_despite_cricket", "the_real_fan"],
        "I know it is IPL. You get one match per week — properly scheduled. "
        "Every other match during work hours: I am here.",
    ),
    SeasonalEvent(
        "Diwali Detox", "2026-10-20", "2026-10-25", 1.0,
        ["ammas_blessing"],
        "Happy Diwali, beta. Take this time. Come back refreshed.",
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# ANTI-ADDICTION SAFEGUARDS (Ch 114)
# ═══════════════════════════════════════════════════════════════════════════════

WALL_TIME_LIMIT_SECONDS = 180  # 3 minutes

WALL_TIME_WARNING = (
    "Beta, you have been looking at your own achievements for 3 minutes. "
    "Get back to earning them."
)


def detect_badge_optimization(session_productive_minutes: List[int]) -> bool:
    """Detect if user stops exactly at 2-hour mark to game resets (Ch 114.3)."""
    if len(session_productive_minutes) < 10:
        return False
    recent = session_productive_minutes[-10:]
    clustering = sum(1 for t in recent if 118 <= t <= 125)
    return clustering >= 7
