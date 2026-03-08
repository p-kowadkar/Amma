"""
Pattern Memory & Black Hole Detection — Ch 18
Tracks recurring distraction sources and escalates when patterns form.
"""
from collections import defaultdict
from datetime import timedelta
from typing import Optional

BLACK_HOLE_MIN_VISITS = 3
BLACK_HOLE_MIN_MINUTES = 30
AMPLIFIED_START_LEVEL = 3  # Skip to L3 for known black holes


class PatternTracker:
    """Tracks per-app distraction frequency and total time."""

    def __init__(self):
        self.timepass_counts: dict[str, int] = defaultdict(int)
        self.timepass_time: dict[str, timedelta] = defaultdict(timedelta)
        self.flagged_black_holes: set[str] = set()

    def record(self, app: str, classification: str, duration: timedelta):
        """Record an observation. Only TIMEPASS contributes to pattern."""
        if classification == "TIMEPASS" and app:
            key = self._normalize(app)
            self.timepass_counts[key] += 1
            self.timepass_time[key] += duration

    def check_black_hole(self, app: str) -> Optional[dict]:
        """Check if app has become a black hole. Returns info dict or None."""
        key = self._normalize(app)
        count = self.timepass_counts.get(key, 0)
        total_time = self.timepass_time.get(key, timedelta())

        is_black_hole = (
            count >= BLACK_HOLE_MIN_VISITS
            and total_time >= timedelta(minutes=BLACK_HOLE_MIN_MINUTES)
            and key not in self.flagged_black_holes
        )

        if is_black_hole:
            self.flagged_black_holes.add(key)
            return {
                "app": app,
                "count": count,
                "total_minutes": int(total_time.total_seconds() / 60),
            }
        return None

    def get_starting_warning_level(self, app: str) -> int:
        """If app is a known black hole, start at L3 instead of L0 (Ch 18.4)."""
        if self._normalize(app) in self.flagged_black_holes:
            return AMPLIFIED_START_LEVEL
        return 0

    def is_black_hole(self, app: str) -> bool:
        return self._normalize(app) in self.flagged_black_holes

    def get_stats(self, app: str) -> dict:
        """Get pattern stats for an app."""
        key = self._normalize(app)
        return {
            "visits": self.timepass_counts.get(key, 0),
            "total_minutes": int(self.timepass_time.get(key, timedelta()).total_seconds() / 60),
            "is_black_hole": key in self.flagged_black_holes,
        }

    @staticmethod
    def _normalize(app: str) -> str:
        return app.lower().strip().replace(" ", "-")
