"""
Special Days & Events — Ch 41
Cultural calendar awareness: festivals, IPL season, exam periods,
birthdays, and event-specific personality adjustments.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Optional, List

# IANA timezone prefixes considered "India" for cultural filtering
_INDIA_TZ_PREFIXES = ("Asia/Kolkata", "Asia/Calcutta", "IST")


def _is_india_timezone(tz_str: str) -> bool:
    """True if timezone string maps to India."""
    return any(tz_str.startswith(p) for p in _INDIA_TZ_PREFIXES)


@dataclass
class SpecialDay:
    name: str
    date_start: date
    date_end: date
    day_type: str          # festival | exam | sports | birthday | religious
    strictness_mod: int    # -3 to +3
    warmth_mod: int        # -2 to +3
    greeting: str          # What Amma says at session start
    work_expectation: str  # normal | reduced | off | increased
    regions: List[str] = field(default_factory=lambda: ["ALL"])  # ["ALL"] or ["IN"] etc.


# ── Indian Cultural Calendar (2026 — update yearly) ──────────────────────────
# Festivals tagged ["ALL"] fire for everyone (diaspora celebrates too).
# Exam seasons and sports tagged ["IN"] only fire when user is in India.

SPECIAL_DAYS_2026: List[SpecialDay] = [
    # Festivals — ALL (diaspora celebrates these everywhere)
    SpecialDay("Makar Sankranti", date(2026, 1, 14), date(2026, 1, 15), "festival",
               -2, 2, "Happy Sankranti, beta. Enjoy today. Light session.", "reduced", ["ALL"]),
    SpecialDay("Republic Day", date(2026, 1, 26), date(2026, 1, 26), "festival",
               -3, 2, "Happy Republic Day. Take the day. You earned it.", "off", ["ALL"]),
    SpecialDay("Holi", date(2026, 3, 17), date(2026, 3, 17), "festival",
               -3, 3, "Happy Holi, beta! Go play. No screens today.", "off", ["ALL"]),
    SpecialDay("Ugadi", date(2026, 3, 29), date(2026, 3, 29), "festival",
               -2, 2, "Ugadi subhashayagalu. New year, new focus.", "reduced", ["ALL"]),
    SpecialDay("Ram Navami", date(2026, 4, 6), date(2026, 4, 6), "religious",
               -1, 1, "Ram Navami today. Finish your pooja first.", "reduced", ["ALL"]),
    SpecialDay("Independence Day", date(2026, 8, 15), date(2026, 8, 15), "festival",
               -3, 2, "Happy Independence Day, beta.", "off", ["ALL"]),
    SpecialDay("Ganesh Chaturthi", date(2026, 8, 27), date(2026, 8, 28), "festival",
               -2, 2, "Ganapati Bappa Morya! Enjoy the festivities.", "reduced", ["ALL"]),
    SpecialDay("Navratri", date(2026, 10, 2), date(2026, 10, 10), "festival",
               -1, 1, "Navratri blessings, beta. Work, but also celebrate.", "normal", ["ALL"]),
    SpecialDay("Dussehra", date(2026, 10, 12), date(2026, 10, 12), "festival",
               -2, 2, "Happy Dussehra. Victory of good over evil. Be the good.", "reduced", ["ALL"]),
    SpecialDay("Diwali", date(2026, 10, 20), date(2026, 10, 22), "festival",
               -3, 3, "Happy Diwali, beta! This is family time. Go.", "off", ["ALL"]),
    SpecialDay("Christmas", date(2026, 12, 25), date(2026, 12, 25), "festival",
               -3, 2, "Merry Christmas, beta. Take the day off.", "off", ["ALL"]),

    # Exam Seasons — IN only (irrelevant for diaspora abroad)
    SpecialDay("Board Exam Season", date(2026, 2, 15), date(2026, 3, 31), "exam",
               2, 0, "Exam season. Every student in India is studying. Including you.", "increased", ["IN"]),
    SpecialDay("JEE/NEET Prep", date(2026, 3, 1), date(2026, 4, 30), "exam",
               2, -1, "Entrance exams are coming. Focus is not optional.", "increased", ["IN"]),
    SpecialDay("Placement Season", date(2026, 8, 1), date(2026, 11, 30), "exam",
               1, 0, "Placement season. Every hour counts.", "increased", ["IN"]),

    # Sports — IN only
    SpecialDay("IPL 2026", date(2026, 3, 22), date(2026, 5, 26), "sports",
               1, 0, "IPL is on. One match per week — properly scheduled. Not during work.", "normal", ["IN"]),
    SpecialDay("T20 World Cup", date(2026, 10, 17), date(2026, 11, 15), "sports",
               0, 0, "World Cup is on. India matches: scheduled breaks. Other matches: no.", "normal", ["IN"]),
]


def get_todays_specials(
    today: Optional[date] = None,
    custom_days: Optional[List[SpecialDay]] = None,
    timezone_str: str = "Asia/Kolkata",
) -> List[SpecialDay]:
    """Get all special days active today, filtered by user's timezone/region."""
    if today is None:
        # Use user's local date, not system date
        try:
            import zoneinfo
            tz = zoneinfo.ZoneInfo(timezone_str)
            today = datetime.now(tz).date()
        except Exception:
            today = date.today()

    is_india = _is_india_timezone(timezone_str)
    all_days = (custom_days or []) + SPECIAL_DAYS_2026
    result = []
    for d in all_days:
        if not (d.date_start <= today <= d.date_end):
            continue
        # Filter region: ALL fires everywhere, IN only fires in India
        if "ALL" in d.regions:
            result.append(d)
        elif "IN" in d.regions and is_india:
            result.append(d)
    return result


def get_strictness_modifier(today: Optional[date] = None, timezone_str: str = "Asia/Kolkata") -> int:
    """Net strictness modifier from all active special days."""
    specials = get_todays_specials(today, timezone_str=timezone_str)
    if not specials:
        return 0
    return min(s.strictness_mod for s in specials)


def get_warmth_modifier(today: Optional[date] = None, timezone_str: str = "Asia/Kolkata") -> int:
    """Net warmth modifier from all active special days."""
    specials = get_todays_specials(today, timezone_str=timezone_str)
    if not specials:
        return 0
    return max(s.warmth_mod for s in specials)


def get_special_greeting(today: Optional[date] = None, timezone_str: str = "Asia/Kolkata") -> Optional[str]:
    """Get the greeting for today's most significant special day."""
    specials = get_todays_specials(today, timezone_str=timezone_str)
    if not specials:
        return None
    priority = {"festival": 0, "birthday": 0, "religious": 1, "exam": 2, "sports": 3}
    specials.sort(key=lambda s: priority.get(s.day_type, 9))
    return specials[0].greeting


def should_reduce_monitoring(today: Optional[date] = None, timezone_str: str = "Asia/Kolkata") -> bool:
    """True if today is a day off — Amma should back off significantly."""
    specials = get_todays_specials(today, timezone_str=timezone_str)
    return any(s.work_expectation == "off" for s in specials)


# ── Birthday support ─────────────────────────────────────────────────────────

def create_birthday_day(birthday: date, name: str = "beta") -> SpecialDay:
    """Create a special day for the user's birthday."""
    return SpecialDay(
        f"{name}'s Birthday",
        birthday, birthday,
        "birthday",
        strictness_mod=-3,
        warmth_mod=3,
        greeting=f"Happy Birthday, {name}! Today is YOUR day. Light session only.",
        work_expectation="reduced",
    )


# ── IPL-specific (Ch 41.3) ──────────────────────────────────────────────────

IPL_MATCH_DIALOGUE = [
    "I know there is a match today. You get the last 5 overs. Not the whole thing.",
    "IPL is not an emergency, beta. The highlights will be there later.",
    "One match per week. We agreed. Which one is it this week?",
]

EXAM_MOTIVATION = [
    "Every student in India is studying right now. Every. Single. One.",
    "The exam does not care about your mood. Open the book.",
    "Three weeks. That is all. Three weeks of absolute focus. You can do this.",
]
