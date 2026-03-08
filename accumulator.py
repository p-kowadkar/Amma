from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

SESSION_CAP_HOURS = 12


@dataclass
class AmmaAccumulator:
    timepass_total: timedelta = field(default_factory=timedelta)
    work_total: timedelta = field(default_factory=timedelta)
    work_streak: timedelta = field(default_factory=timedelta)
    session_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    scold_reset_at: Optional[datetime] = None
    warning_level: int = 0
    in_break: bool = False
    break_start: Optional[datetime] = None
    last_classification: str = "WORK"
    # Phase 1 additions
    peak_warning_level: int = 0
    longest_work_streak: timedelta = field(default_factory=timedelta)

    def update(self, classification: str, now: Optional[datetime] = None) -> dict:
        now = now or datetime.now(timezone.utc)
        elapsed = now - self.last_update
        # Cap gap at 15 min (sleep/away detection) — spec says elapsed = 0
        if elapsed > timedelta(minutes=15):
            elapsed = timedelta(0)
        result = {"intervention": None, "level_changed": False}

        if self.in_break:
            self.last_update = now
            return result
        if classification == "GREY":
            self.last_update = now
            return result

        if classification == "TIMEPASS":
            self.timepass_total += elapsed
            self.work_streak = timedelta(0)
        elif classification == "WORK":
            self.work_total += elapsed
            self.work_streak += elapsed
            # Track longest work streak for end-of-session stats
            if self.work_streak > self.longest_work_streak:
                self.longest_work_streak = self.work_streak
            if self.work_streak >= timedelta(hours=2):
                self._reset_scold_counter(now)
                result["intervention"] = "RESET_PRAISE"

        self.last_classification = classification
        self.last_update = now

        new_level = self._calculate_warning_level()
        if new_level != self.warning_level:
            self.warning_level = new_level
            result["level_changed"] = True
            result["intervention"] = f"WARNING{new_level}"
        # Track peak warning level
        if self.warning_level > self.peak_warning_level:
            self.peak_warning_level = self.warning_level
        return result

    def _calculate_warning_level(self) -> int:
        minutes = self.timepass_total.total_seconds() / 60
        if minutes >= 105: return 5
        if minutes >= 90:  return 4
        if minutes >= 75:  return 3
        if minutes >= 60:  return 2
        if minutes >= 45:  return 1
        return 0

    def _reset_scold_counter(self, now: datetime):
        self.timepass_total = timedelta(0)
        self.warning_level = 0
        self.scold_reset_at = now

    def start_break(self):
        self.in_break = True
        self.break_start = datetime.now(timezone.utc)

    def end_break(self):
        self.in_break = False
        self.break_start = None

    @property
    def break_minutes(self) -> int:
        """How long the current break has lasted."""
        if not self.in_break or not self.break_start:
            return 0
        return int((datetime.now(timezone.utc) - self.break_start).total_seconds() / 60)

    def skip_time_for_demo(self, minutes: int):
        """Demo mode: manually advance the timepass accumulator."""
        self.timepass_total += timedelta(minutes=minutes)
        self.warning_level = self._calculate_warning_level()

    @property
    def timepass_minutes(self) -> int:
        return int(self.timepass_total.total_seconds() / 60)

    @property
    def work_minutes(self) -> int:
        return int(self.work_total.total_seconds() / 60)

    @property
    def session_duration(self) -> timedelta:
        return datetime.now(timezone.utc) - self.session_start

    def session_exceeded(self, cap_hours: int = SESSION_CAP_HOURS) -> bool:
        """True if session has exceeded the hard cap."""
        return self.session_duration >= timedelta(hours=cap_hours)

    @property
    def longest_work_streak_minutes(self) -> int:
        return int(self.longest_work_streak.total_seconds() / 60)
