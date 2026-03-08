"""
Trust Score System — Ch 21
Calculated from: snapback rate, nuclear frequency, excuse patterns,
grey zone accuracy, and consistency signals.
Trust score ranges 0.0-1.0 and affects Amma's patience/tone.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class TrustInputs:
    """Raw inputs for trust calculation."""
    total_sessions: int = 0
    snapback_count: int = 0           # Times user self-corrected
    nuclear_count: int = 0            # NUCLEAR events
    timepass_total_minutes: int = 0
    work_total_minutes: int = 0
    excuses_used: int = 0
    excuses_validated: int = 0        # Excuses that turned out legitimate
    grey_zone_declared_work: int = 0  # User declared grey as work
    grey_zone_actually_work: int = 0  # Those that were genuinely work
    streak_days: int = 0
    grace_tokens_used: int = 0


def calculate_trust_score(inputs: TrustInputs) -> float:
    """Calculate trust score 0.0-1.0 from behavioral signals (Ch 21.2).

    Components (weighted):
    - Snapback rate (30%): how often user self-corrects after warnings
    - Nuclear frequency (20%): fewer nuclears = more trust
    - Work ratio (20%): time spent working vs timepass
    - Excuse accuracy (15%): are excuses legitimate or gaming
    - Consistency (15%): streak length, grace token usage
    """
    # 1. Snapback rate (0-1, higher is better)
    total_incidents = inputs.snapback_count + inputs.nuclear_count
    if total_incidents > 0:
        snapback_rate = inputs.snapback_count / total_incidents
    else:
        snapback_rate = 0.5  # Neutral if no data

    # 2. Nuclear penalty (0-1, fewer nuclears is better)
    if inputs.total_sessions > 0:
        nuclear_per_session = inputs.nuclear_count / inputs.total_sessions
        nuclear_score = max(0.0, 1.0 - nuclear_per_session * 2)
    else:
        nuclear_score = 0.5

    # 3. Work ratio (0-1)
    total_time = inputs.work_total_minutes + inputs.timepass_total_minutes
    if total_time > 0:
        work_ratio = inputs.work_total_minutes / total_time
    else:
        work_ratio = 0.5

    # 4. Excuse accuracy (0-1, honest excuses = higher trust)
    if inputs.excuses_used > 0:
        excuse_accuracy = inputs.excuses_validated / inputs.excuses_used
    else:
        excuse_accuracy = 0.5  # No excuses = neutral

    # 5. Consistency (0-1, streaks + low grace usage = higher)
    streak_score = min(1.0, inputs.streak_days / 30)  # 30-day streak = max
    grace_penalty = min(1.0, inputs.grace_tokens_used * 0.15)
    consistency = max(0.0, streak_score - grace_penalty)

    # Weighted total
    trust = (
        snapback_rate * 0.30
        + nuclear_score * 0.20
        + work_ratio * 0.20
        + excuse_accuracy * 0.15
        + consistency * 0.15
    )

    return round(max(0.0, min(1.0, trust)), 3)


def trust_to_patience(trust: float, base_patience_minutes: int = 45) -> int:
    """Convert trust score to patience minutes (Ch 21.4).
    High trust = more patience before escalation.
    Low trust = faster escalation."""
    multiplier = 0.5 + trust  # 0.5x at trust=0, 1.5x at trust=1
    return int(base_patience_minutes * multiplier)


def trust_to_label(trust: float) -> str:
    """Human-readable trust level."""
    if trust >= 0.85:
        return "EXEMPLARY"
    if trust >= 0.70:
        return "TRUSTED"
    if trust >= 0.50:
        return "BUILDING"
    if trust >= 0.30:
        return "WATCHING"
    return "PROBATION"


TRUST_DIALOGUE = {
    "EXEMPLARY": "I trust you, beta. You have earned it.",
    "TRUSTED": "You are getting there. I see the effort.",
    "BUILDING": "I am watching. Show me consistency.",
    "WATCHING": "You have some work to do to earn my trust back.",
    "PROBATION": "Beta. We need to talk about what has been happening.",
}
