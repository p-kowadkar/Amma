"""
Time-of-Day Personality Shifts — Ch 42
Daily personality arc: how Amma changes from 6am to 4am.
"""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional
from zoneinfo import ZoneInfo


@dataclass
class TimeWindow:
    name: str
    start_hour: int   # inclusive
    end_hour: int      # exclusive
    description: str
    strictness_mod: int  # modifier to base strictness
    warmth_mod: int
    priority: str      # what Amma focuses on
    greeting: str


# Ch 42 time windows
TIME_WINDOWS = [
    TimeWindow("EARLY_BIRD",      5,  7,  "Impressed but slightly worried",  0,  1,  "wellbeing", "Beta, you are up early. Good. Or concerning. Which is it?"),
    TimeWindow("MORNING_LAUNCH",  7,  9,  "Energetic, structured",           0,  0,  "goals",     "Good morning. Before you open anything — listen to me."),
    TimeWindow("PEAK_HOURS",      9,  12, "Standard Guard Mode",             0,  0,  "productivity", ""),
    TimeWindow("LUNCH_WINDOW",    12, 13, "Brief patience",                  -1, 1,  "health",    "Beta, go eat something. 20 minutes. Then back."),
    TimeWindow("AFTERNOON_GRIND", 13, 16, "Watchful, steady",                0,  0,  "productivity", ""),
    TimeWindow("END_OF_DAY_PUSH", 16, 18, "Slightly urgent",                 1,  0,  "closing",   "Two hours left of proper work time."),
    TimeWindow("EVENING",         18, 21, "Flexible, aware",                 -1, 1,  "transition", ""),
    TimeWindow("LATE_NIGHT",      21, 23, "Increasingly firm",               0,  0,  "sleep",     "Beta, it is getting late. Wrap up properly."),
    TimeWindow("MIDNIGHT",        23, 1,  "Disapproving",                    0,  1,  "sleep",     "It is late. I should not have to say this. Sleep."),
    TimeWindow("LATE_LATE",       1,  3,  "Full concern",                    -2, 3,  "wellbeing", "Beta. This is not acceptable. Close everything. Now. Sleep."),
    TimeWindow("ALARM",           3,  5,  "Alarm, not anger — abandon productivity focus", -3, 5, "crisis", "Whatever you are doing — it is not worth this. SLEEP."),
]


def get_current_window(tz_name: str = "Asia/Kolkata",
                       now: Optional[datetime] = None) -> TimeWindow:
    """Get the active time window for the current hour."""
    now = now or datetime.now(timezone.utc)
    try:
        local = now.astimezone(ZoneInfo(tz_name))
    except Exception:
        local = now  # Fall back to UTC
    hour = local.hour

    for tw in TIME_WINDOWS:
        if tw.start_hour < tw.end_hour:
            # Normal range (e.g. 9-12)
            if tw.start_hour <= hour < tw.end_hour:
                return tw
        else:
            # Wraps midnight (e.g. 23-1)
            if hour >= tw.start_hour or hour < tw.end_hour:
                return tw

    # Default: peak hours
    return TIME_WINDOWS[2]


def is_3pm_slump(tz_name: str = "Asia/Kolkata",
                 now: Optional[datetime] = None) -> bool:
    """Detect the 3pm slump window (14:30 – 15:30)."""
    now = now or datetime.now(timezone.utc)
    try:
        local = now.astimezone(ZoneInfo(tz_name))
    except Exception:
        local = now
    return 14 <= local.hour <= 15 and local.minute >= 30 if local.hour == 14 else local.hour == 15


def is_alarm_hours(tz_name: str = "Asia/Kolkata",
                   now: Optional[datetime] = None) -> bool:
    """True if it's 2am+ — Amma should abandon productivity, focus on wellbeing."""
    now = now or datetime.now(timezone.utc)
    try:
        local = now.astimezone(ZoneInfo(tz_name))
    except Exception:
        local = now
    return 2 <= local.hour < 5


# ── Slump commentary ────────────────────────────────────────────────────────
SLUMP_LINES = [
    "It is {day_name} afternoon. You usually hit a wall now. Push through.",
    "3pm energy crash. I see it every day. Get water. Stand up. Then continue.",
    "The slump is here. Do not give in. Ten more minutes. Then evaluate.",
]

LATE_NIGHT_LINES = [
    "Beta, it is getting late. Wrap up properly, not just minimize and continue.",
    "How much longer? Give me a number. I am holding you to it.",
    "After this task — sleep. That is an order, not a suggestion.",
]

ALARM_LINES = [
    "Whatever you are doing — it is not worth this. SLEEP.",
    "Beta. I am not going to scold you at 3am. I am going to worry. Please sleep.",
    "This is not healthy. I do not care about the work right now. Sleep.",
]
