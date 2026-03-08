"""
Guard Mode vs Support Mode — Ch 27
Automatic mode detection from context signals.
Support Mode: pauses timers, switches voice, emotional conversation.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List


class AmmaMode(str, Enum):
    GUARD = "GUARD"
    SUPPORT = "SUPPORT"
    CRISIS = "CRISIS"


# Context signals that trigger mode switches (Ch 27.2)
SUPPORT_TRIGGERS = [
    "rejection_email",
    "stress_typing",         # rapid deletes, long pauses
    "late_night_no_output",  # 3am+ with no work
    "user_distress_statement",
    "sad_music_detected",
    "extended_inactivity_post_failure",
]

CRISIS_SIGNALS = [
    "repeated_searches_concerning_topics",
    "unusual_hours_plus_emotional_audio",
    "sudden_complete_inactivity_post_distress",
    "direct_statement_of_distress",
]


@dataclass
class SupportModeManager:
    """Manages Guard ↔ Support ↔ Crisis mode transitions."""

    mode: AmmaMode = AmmaMode.GUARD
    support_activated_at: Optional[datetime] = None
    crisis_activated_at: Optional[datetime] = None
    active_signals: List[str] = field(default_factory=list)
    _signal_history: List[dict] = field(default_factory=list)

    def add_signal(self, signal: str, now: Optional[datetime] = None) -> Optional[AmmaMode]:
        """Record a context signal. Returns new mode if transition occurred."""
        now = now or datetime.now(timezone.utc)
        self._signal_history.append({"signal": signal, "ts": now})
        if signal not in self.active_signals:
            self.active_signals.append(signal)

        # Crisis check: 2+ crisis signals cluster
        crisis_count = sum(1 for s in self.active_signals if s in CRISIS_SIGNALS)
        if crisis_count >= 2 and self.mode != AmmaMode.CRISIS:
            return self._enter_crisis(now)

        # Support check: any support trigger
        if signal in SUPPORT_TRIGGERS and self.mode == AmmaMode.GUARD:
            return self._enter_support(now)

        return None

    def _enter_support(self, now: datetime) -> AmmaMode:
        self.mode = AmmaMode.SUPPORT
        self.support_activated_at = now
        return AmmaMode.SUPPORT

    def _enter_crisis(self, now: datetime) -> AmmaMode:
        self.mode = AmmaMode.CRISIS
        self.crisis_activated_at = now
        return AmmaMode.CRISIS

    def return_to_guard(self) -> AmmaMode:
        """User signals readiness to return to work."""
        self.mode = AmmaMode.GUARD
        self.active_signals.clear()
        self.support_activated_at = None
        self.crisis_activated_at = None
        return AmmaMode.GUARD

    @property
    def is_guard(self) -> bool:
        return self.mode == AmmaMode.GUARD

    @property
    def is_support(self) -> bool:
        return self.mode == AmmaMode.SUPPORT

    @property
    def is_crisis(self) -> bool:
        return self.mode == AmmaMode.CRISIS

    @property
    def recommended_voice(self) -> str:
        """Returns recommended Gemini voice for current mode."""
        if self.mode == AmmaMode.CRISIS:
            return "Kore"    # Softest
        if self.mode == AmmaMode.SUPPORT:
            return "Kore"    # Warm, gentle
        return "Aoede"       # Default Guard mode


# ── Support/Crisis dialogue ─────────────────────────────────────────────────
SUPPORT_DIALOGUE = {
    "rejection_email": [
        "Beta, I saw that email. Sit with me for a moment.",
        "I know that email was not what you wanted. It is okay. Talk to me.",
    ],
    "stress_typing": [
        "Beta, are you stuck? Talk to me. What is the problem?",
        "I can see you struggling. Take a breath. Tell me what is wrong.",
    ],
    "late_night_no_output": [
        "Beta, why are you still awake? What is going on?",
        "It is very late. Whatever this is, it can wait until morning.",
    ],
    "user_distress_statement": [
        "I hear you. I am here. What do you need right now?",
        "Stop whatever you are doing. Talk to me. I am here.",
    ],
    "crisis": [
        "Beta, stop whatever you are doing. Talk to me. I am here. What is happening right now?",
        "Everything else can wait. I am here. Tell me what you need.",
    ],
}
