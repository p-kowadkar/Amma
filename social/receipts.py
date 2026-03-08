"""
Shareable Amma Receipts — Ch 62
Weekly receipt cards designed for social sharing.
"""
from dataclasses import dataclass
from datetime import datetime
import random


PRIDE_NOTES = [
    "Not bad, beta. Not bad at all. I am telling people about this week.",
    "I did not think you had it in you this week. You proved me wrong.",
    "The Council is watching. They are nodding. Do not stop.",
]

SHAME_NOTES = [
    "Beta, I cannot explain this week. I have tried. I have no words. Next week is a new week. Use it.",
    "The Council has been informed. I have nothing more to say.",
    "We both know what happened. We do not need to discuss it further.",
]

NEUTRAL_NOTES = [
    "Average. Not terrible. Not great. You can do better and we both know it.",
    "Middle of the road. Push harder next week.",
]


@dataclass
class AmmaReceipt:
    user_name: str
    week_label: str          # e.g. "Week of Mar 3, 2026"
    focus_pct: int           # 0-100
    best_streak: str         # e.g. "4 hrs 20 min"
    times_screamed: int
    council_verdict: str     # "Hall of Pride" | "Hall of Shame" | "Neutral"
    amma_note: str


def generate_receipt(
    user_name: str,
    week_label: str,
    focus_pct: int,
    best_streak_min: int,
    scream_count: int,
    hall_status: str,
) -> AmmaReceipt:
    hours = best_streak_min // 60
    mins = best_streak_min % 60
    streak_str = f"{hours} hrs {mins} min" if hours > 0 else f"{mins} min"

    if hall_status == "pride":
        verdict = "Hall of Pride"
        note = random.choice(PRIDE_NOTES)
    elif hall_status == "shame":
        verdict = "HALL OF SHAME"
        note = random.choice(SHAME_NOTES)
    else:
        verdict = "Neutral"
        note = random.choice(NEUTRAL_NOTES)

    return AmmaReceipt(
        user_name=user_name,
        week_label=week_label,
        focus_pct=focus_pct,
        best_streak=streak_str,
        times_screamed=scream_count,
        council_verdict=verdict,
        amma_note=note,
    )
