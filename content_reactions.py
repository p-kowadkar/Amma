"""
Content Reactions — Ch 33
Detect educational/productive content and react contextually.
"Are you taking notes?" protocol, lecture awareness, tutorial tracking.
"""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, List


# ── Educational content markers (Ch 33.2) ────────────────────────────────────

EDUCATIONAL_KEYWORDS = [
    "tutorial", "lecture", "course", "lesson", "udemy", "coursera",
    "khan academy", "mit ocw", "edx", "pluralsight", "freecodecamp",
    "documentation", "docs", "api reference", "man page", "readme",
    "how to", "guide", "walkthrough",
]

PRODUCTIVE_MEDIA_KEYWORDS = [
    "conference talk", "tech talk", "keynote", "webinar", "workshop",
    "podcast", "interview", "panel discussion",
]

PASSIVE_CONSUMPTION_KEYWORDS = [
    "youtube", "twitch", "netflix", "hotstar", "prime video",
    "reddit", "hacker news", "twitter", "instagram",
]


def detect_content_type(window_title: str, dominant_app: str = "") -> str:
    """Classify content as EDUCATIONAL / PRODUCTIVE_MEDIA / PASSIVE / UNKNOWN."""
    combined = f"{window_title} {dominant_app}".lower()

    if any(k in combined for k in EDUCATIONAL_KEYWORDS):
        return "EDUCATIONAL"
    if any(k in combined for k in PRODUCTIVE_MEDIA_KEYWORDS):
        return "PRODUCTIVE_MEDIA"
    if any(k in combined for k in PASSIVE_CONSUMPTION_KEYWORDS):
        return "PASSIVE"
    return "UNKNOWN"


# ── Content Reaction Engine (Ch 33.3) ────────────────────────────────────────

@dataclass
class ContentReactionState:
    """Tracks content-aware reactions within a session."""
    current_content_type: str = "UNKNOWN"
    content_start_ts: Optional[datetime] = None
    notes_check_fired: bool = False
    notes_check_count: int = 0
    _last_content_app: str = ""

    def update(self, window_title: str, dominant_app: str = "") -> Optional[str]:
        """Process a frame and return a reaction key if one should fire, else None."""
        now = datetime.now(timezone.utc)
        content_type = detect_content_type(window_title, dominant_app)

        # Content type changed
        if content_type != self.current_content_type or dominant_app != self._last_content_app:
            self.current_content_type = content_type
            self._last_content_app = dominant_app
            self.content_start_ts = now
            self.notes_check_fired = False
            return None

        if content_type == "UNKNOWN" or self.content_start_ts is None:
            return None

        elapsed = (now - self.content_start_ts).total_seconds() / 60

        # Educational content: "are you taking notes?" after 15 minutes
        if content_type == "EDUCATIONAL" and elapsed >= 15 and not self.notes_check_fired:
            self.notes_check_fired = True
            self.notes_check_count += 1
            return "NOTES_CHECK"

        # Productive media (talks/podcasts): lighter check after 30 minutes
        if content_type == "PRODUCTIVE_MEDIA" and elapsed >= 30 and not self.notes_check_fired:
            self.notes_check_fired = True
            return "MEDIA_CHECK"

        # Passive consumption: escalation after 20 minutes of "grey" viewing
        if content_type == "PASSIVE" and elapsed >= 20 and not self.notes_check_fired:
            self.notes_check_fired = True
            return "PASSIVE_WARNING"

        return None


# ── Reaction dialogue ────────────────────────────────────────────────────────

CONTENT_REACTIONS = {
    "NOTES_CHECK": [
        "Beta, you have been watching this tutorial for a while. Are you taking notes?",
        "I see a course open. Are you actually following along or just watching?",
        "Fifteen minutes of tutorial. Quick check — have you tried it yourself yet?",
    ],
    "MEDIA_CHECK": [
        "Good talk. Are you going to apply any of this today?",
        "I see you watching a tech talk. Make sure something sticks.",
    ],
    "PASSIVE_WARNING": [
        "Beta, this does not look like work to me. Prove me wrong.",
        "Twenty minutes of this. I am starting to have opinions.",
    ],
    "CONTENT_PRAISE": [
        "I see you learning something new. Good. Keep going.",
        "Tutorial and code editor open at the same time. This is exactly right.",
    ],
}


def get_content_reaction(reaction_key: str) -> str:
    """Get a random reaction line for the given key."""
    import random
    lines = CONTENT_REACTIONS.get(reaction_key, [])
    return random.choice(lines) if lines else ""
