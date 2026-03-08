"""
Break Mode Manager — Ch 35 Full Specification
Timed check-ins, auto-expiry at 75 min, dialogue ladder.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from accumulator import AmmaAccumulator
from dialogue import get_line, get_volume

# Break duration ladder thresholds (minutes)
BREAK_CHECKIN_THRESHOLDS = [15, 30, 45, 60]
BREAK_AUTO_EXPIRE_MINUTES = 75


class BreakModeManager:
    def __init__(self, accumulator: AmmaAccumulator):
        self.accumulator = accumulator
        self.break_start: Optional[datetime] = None
        self.check_in_fired: dict[int, bool] = {t: False for t in BREAK_CHECKIN_THRESHOLDS}

    def activate(self, now: Optional[datetime] = None):
        now = now or datetime.now(timezone.utc)
        self.accumulator.in_break = True
        self.accumulator.break_start = now
        self.break_start = now
        self.check_in_fired = {t: False for t in BREAK_CHECKIN_THRESHOLDS}

    def deactivate(self):
        self.accumulator.in_break = False
        self.accumulator.break_start = None
        self.break_start = None

    @property
    def is_active(self) -> bool:
        return self.break_start is not None and self.accumulator.in_break

    @property
    def break_minutes(self) -> int:
        if not self.break_start:
            return 0
        return int((datetime.now(timezone.utc) - self.break_start).total_seconds() / 60)

    def get_pending_intervention(self, now: Optional[datetime] = None) -> Optional[dict]:
        """Check if a break check-in is due. Returns intervention dict or None."""
        if not self.break_start:
            return None
        now = now or datetime.now(timezone.utc)
        minutes = (now - self.break_start).total_seconds() / 60

        # Auto-expire at 75 min — resume monitoring
        if minutes >= BREAK_AUTO_EXPIRE_MINUTES:
            self.deactivate()
            return {
                "type": "BREAK_EXPIRED",
                "line": get_line("BREAK_EXPIRED"),
                "volume": get_volume("BREAK_EXPIRED"),
            }

        # Check-in ladder: 15, 30, 45, 60
        for threshold in BREAK_CHECKIN_THRESHOLDS:
            if minutes >= threshold and not self.check_in_fired[threshold]:
                self.check_in_fired[threshold] = True
                intervention_type = f"BREAK_CHECKIN_{threshold}"
                return {
                    "type": intervention_type,
                    "line": get_line(intervention_type),
                    "volume": get_volume(intervention_type),
                }

        return None
