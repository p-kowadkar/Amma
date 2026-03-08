from datetime import datetime, timedelta, timezone
from typing import Optional
from accumulator import AmmaAccumulator
from dialogue import get_line, get_volume, get_snapback_type

WARNING_STATES = {"WARNING1", "WARNING2", "WARNING3", "WARNING4", "SCREAM", "NUCLEAR"}
MIN_STATE_DURATION = 30  # seconds — prevents micro-flicker (Ch 34.3)


class AmmaStateMachine:
    def __init__(self, debounce_seconds: int = 0):
        self.state = "IDLE"
        self.accumulator = AmmaAccumulator()
        self.last_intervention_ts: Optional[datetime] = None
        self.last_intervention_level: int = 0
        self.last_classification: str = "WORK"
        self.prev_state: str = "IDLE"
        # Debounce (Ch 34.3)
        self.debounce_seconds = debounce_seconds
        self._confirmed_cls: Optional[str] = None
        self._pending_cls: Optional[str] = None
        self._pending_since: Optional[datetime] = None

    def process(self, classification: str, now: Optional[datetime] = None) -> Optional[dict]:
        """
        Process a new classification. Returns an intervention dict or None.
        dict = {"type": str, "line": str, "volume": float}
        """
        now = now or datetime.now(timezone.utc)

        # Debounce: require consistent classification for N seconds (Ch 34.3)
        if self.debounce_seconds > 0:
            effective = self._debounce(classification, now)
            if effective is None:
                # Still debouncing — update timestamp to prevent gap accumulation
                self.accumulator.last_update = now
                return None
            classification = effective

        prev_state = self.state
        result = self.accumulator.update(classification, now)
        self.last_classification = classification

        # Snap-back detection: was in any warning/scream state, now working
        if classification == "WORK" and prev_state in WARNING_STATES:
            level = max(self.accumulator.warning_level, 1)
            snapback_type = get_snapback_type(level)
            self.state = "WORKING"
            return {
                "type": snapback_type,
                "line": get_line(snapback_type),
                "volume": get_volume(snapback_type),
            }

        # Reset praise (2h solid work)
        if result["intervention"] == "RESET_PRAISE":
            self.state = "RESET"
            return {
                "type": "RESET_PRAISE",
                "line": get_line("RESET_PRAISE"),
                "volume": get_volume("RESET_PRAISE"),
            }

        # State based on classification
        if classification == "WORK":
            self.state = "WORKING"
        elif classification == "TIMEPASS":
            level = self.accumulator.warning_level
            if level == 0:
                self.state = "WORKING"  # Under threshold, no warning yet
            elif level == 5:
                self.state = "SCREAM"
            else:
                self.state = f"WARNING{level}"
        elif classification == "GREY":
            self.state = "GREY_PENDING"
        elif classification == "BREAK":
            self.state = "BREAK"

        # Fire new level intervention
        if result["level_changed"] and result["intervention"]:
            intervention_type = result["intervention"]
            if self.accumulator.warning_level == 5:
                intervention_type = "WARNING5"
            self.last_intervention_ts = datetime.now(timezone.utc)
            self.last_intervention_level = self.accumulator.warning_level
            return {
                "type": intervention_type,
                "line": get_line(intervention_type),
                "volume": get_volume(intervention_type),
            }

        # Repeat intervention for ongoing timepass
        if self.state in WARNING_STATES:
            return self._check_repeat()

        return None

    def process_nuclear(self, config=None) -> dict:
        """Immediate NUCLEAR intervention — triggered by classifier or command.

        Ch 26: full name trigger after 2 repeat nuclear events.
        Nuclear repeat interval: 30 seconds.
        """
        self.state = "NUCLEAR"
        now = datetime.now(timezone.utc)
        self.last_intervention_ts = now
        self.nuclear_count = getattr(self, "nuclear_count", 0) + 1

        # Full name trigger after 2+ nuclear events (Ch 26.4)
        if self.nuclear_count >= 3 and config and hasattr(config, "full_name"):
            line = f"{config.full_name}. I know exactly what is happening right now. Close it."
        else:
            line = get_line("NUCLEAR")

        return {
            "type": "NUCLEAR",
            "line": line,
            "volume": get_volume("NUCLEAR"),
        }

    def _check_repeat(self) -> Optional[dict]:
        now = datetime.now(timezone.utc)
        level = self.accumulator.warning_level
        # Nuclear: 30s repeat (Ch 26.2); Level 5: 2 min; Level 4: 5 min; others: 10 min
        if self.state == "NUCLEAR":
            interval = timedelta(seconds=30)
        else:
            intervals = {5: 2, 4: 5, 3: 10, 2: 10, 1: 10}
            interval = timedelta(minutes=intervals.get(level, 10))
        if self.last_intervention_ts is None or (now - self.last_intervention_ts) >= interval:
            self.last_intervention_ts = now
            t = "WARNING5" if level == 5 else f"WARNING{level}"
            return {"type": t, "line": get_line(t), "volume": get_volume(t)}
        return None

    def start_break(self):
        self.state = "BREAK"
        self.accumulator.start_break()

    def end_break(self):
        self.state = "WORKING"
        self.accumulator.end_break()

    # ── Debounce (Ch 34.3) ───────────────────────────────────────────
    def _debounce(self, classification: str, now: datetime) -> Optional[str]:
        """Returns effective classification, or None if still debouncing a transition."""
        # First classification — accept immediately
        if self._confirmed_cls is None:
            self._confirmed_cls = classification
            self._pending_cls = classification
            self._pending_since = now
            return classification

        # Same as confirmed — reset pending, pass through
        if classification == self._confirmed_cls:
            self._pending_cls = classification
            self._pending_since = now
            return classification

        # Different from confirmed — debounce
        if classification == self._pending_cls:
            # Same as pending — check if min duration met
            elapsed = (now - self._pending_since).total_seconds()
            if elapsed >= self.debounce_seconds:
                self._confirmed_cls = classification
                return classification
            return None  # still debouncing

        # New pending classification
        self._pending_cls = classification
        self._pending_since = now
        return None  # start debounce
