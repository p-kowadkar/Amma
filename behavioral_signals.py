"""
Behavioral Signal Stack — Ch 19-20
Phone-side risk scoring from indirect signals. No raw data leaves device.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

# ── Signal definitions (Ch 19.2) ────────────────────────────────────────────

APP_RISK = {
    "dating": 4, "streaming": 4, "social_feed": 2, "browser": 1,
    "incognito": 5, "unknown_new": 2, "obsessive_reopen": 3,
}

BEHAVIORAL_RISK = {
    "brightness_reduced": 3, "headphones_volume_down": 3,
    "landscape_non_video": 2, "doom_scroll": 3,
    "face_down_after_notification": 4, "session_over_20min": 3,
    "rapid_app_switches": 2,
}

TIME_BONUS = {
    "late_night": 2,         # 11pm-4am
    "during_work_hours": 2,  # Calendar-aware
    "post_scold_defiance": 3,  # Same app within 30min of scold
    "laptop_dark_phone_active": 2,
}


@dataclass
class Signal:
    category: str  # app | behavioral | time
    name: str
    weight: int
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


def calculate_risk_score(signals: List[Signal]) -> int:
    """Calculate phone risk level 0-5 from collected signals (Ch 19.3)."""
    raw = sum(s.weight for s in signals)
    if raw == 0:  return 0
    if raw <= 2:  return 1
    if raw <= 5:  return 2
    if raw <= 8:  return 3
    if raw <= 12: return 4
    return 5


def classify_risk_category(signals: List[Signal]) -> str:
    """Determine dominant category: social | adult | gaming | other."""
    categories = [s.name for s in signals]
    if "incognito" in categories or "dating" in categories:
        return "adult"
    if "social_feed" in categories or "doom_scroll" in categories:
        return "social"
    if "streaming" in categories:
        return "gaming"
    return "other"


def build_phone_report(signals: List[Signal]) -> dict:
    """Build the privacy-safe report to send to Cloud Brain.
    Only risk_level (0-5), category, and timestamp. NEVER raw signals."""
    return {
        "risk_level": calculate_risk_score(signals),
        "category": classify_risk_category(signals),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
