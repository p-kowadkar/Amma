"""
Life Integration Layer — Ch 73-83
Calendar, email intelligence, notifications, Notion/Linear, Spotify, browser extension,
smart home, health/wearable, contact awareness, and the Life Context Engine.
"""
from dataclasses import dataclass, field
from datetime import datetime, date, timezone, timedelta
from typing import Optional, List
import random


# ═══════════════════════════════════════════════════════════════════════════════
# CALENDAR INTEGRATION (Ch 73)
# ═══════════════════════════════════════════════════════════════════════════════

EVENT_TYPE_KEYWORDS = {
    "INTERVIEW": ["interview", "chat with", "call with", "screening"],
    "DEADLINE": ["deadline", "due", "submit", "launch", "release"],
    "DEEP_WORK": ["focus", "deep work", "no meetings", "blocked"],
    "BREAK": ["lunch", "break", "gym", "walk", "coffee"],
    "PRESENTATION": ["presentation", "demo", "present", "talk", "speak"],
}


@dataclass
class CalendarEvent:
    title: str
    start: datetime
    end: datetime
    location: Optional[str] = None
    attendees: int = 1
    event_type: str = "UNKNOWN"

    @property
    def duration_min(self) -> float:
        return (self.end - self.start).total_seconds() / 60

    def classify(self) -> str:
        title_lower = self.title.lower()
        for etype, keywords in EVENT_TYPE_KEYWORDS.items():
            if any(k in title_lower for k in keywords):
                return etype
        if self.attendees > 1 and self.duration_min < 120:
            return "MEETING"
        return "GENERAL"


class CalendarIntegration:
    """Stub for Google Calendar / Outlook / Apple Calendar."""

    def __init__(self, provider: str = "google"):
        self.provider = provider
        self.events: List[CalendarEvent] = []

    async def sync_today(self) -> List[CalendarEvent]:
        """Fetch today's events from the configured calendar provider."""
        # TODO: implement OAuth + actual API calls
        return self.events

    def get_upcoming(self, minutes: int = 30) -> List[CalendarEvent]:
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(minutes=minutes)
        return [e for e in self.events if now <= e.start <= cutoff]

    def get_current(self) -> Optional[CalendarEvent]:
        now = datetime.now(timezone.utc)
        for e in self.events:
            if e.start <= now <= e.end:
                return e
        return None


# ── Deadline Urgency Ladder (Ch 36) ──────────────────────────────────────────

def calculate_deadline_urgency(deadline: datetime,
                               now: Optional[datetime] = None) -> dict:
    """Calculate urgency level and strictness multiplier from deadline proximity.

    Returns {level, hours_remaining, strictness_multiplier, dialogue}
    """
    now = now or datetime.now(timezone.utc)
    remaining = deadline - now
    hours = remaining.total_seconds() / 3600

    if hours <= 0:
        return {
            "level": "OVERDUE",
            "hours_remaining": 0,
            "strictness_multiplier": 1.5,
            "dialogue": "Beta. The deadline has PASSED. What is happening.",
        }
    if hours <= 2:
        return {
            "level": "CRITICAL",
            "hours_remaining": round(hours, 1),
            "strictness_multiplier": 1.5,
            "dialogue": f"Two hours. You have two hours until deadline. FOCUS.",
        }
    if hours <= 6:
        return {
            "level": "HIGH",
            "hours_remaining": round(hours, 1),
            "strictness_multiplier": 1.3,
            "dialogue": f"Deadline in {int(hours)} hours. No timepass today.",
        }
    if hours <= 24:
        return {
            "level": "ELEVATED",
            "hours_remaining": round(hours, 1),
            "strictness_multiplier": 1.15,
            "dialogue": "Deadline tomorrow. Today is the day to finish.",
        }
    if hours <= 72:
        return {
            "level": "AWARE",
            "hours_remaining": round(hours, 1),
            "strictness_multiplier": 1.0,
            "dialogue": f"Deadline in {int(hours / 24)} days. Plan accordingly.",
        }
    return {
        "level": "NORMAL",
        "hours_remaining": round(hours, 1),
        "strictness_multiplier": 1.0,
        "dialogue": None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL INTELLIGENCE (Ch 74)
# ═══════════════════════════════════════════════════════════════════════════════

EMAIL_PATTERNS = {
    "REJECTION": {
        "subject_keywords": ["unfortunately", "regret", "not moving forward",
                             "other candidates", "not selected"],
        "response_mode": "SUPPORT",
    },
    "OFFER": {
        "subject_keywords": ["offer", "congratulations", "pleased to inform",
                             "welcome aboard"],
        "response_mode": "CELEBRATION",
    },
    "DEADLINE": {
        "subject_keywords": ["due", "reminder", "deadline", "overdue"],
        "response_mode": "URGENCY",
    },
}


@dataclass
class EmailEvent:
    subject: str
    sender_domain: str
    timestamp: datetime
    event_type: str = "UNKNOWN"
    sentiment: str = "neutral"  # positive | negative | neutral

    def classify(self) -> str:
        subj_lower = self.subject.lower()
        for etype, cfg in EMAIL_PATTERNS.items():
            if any(k in subj_lower for k in cfg["subject_keywords"]):
                return etype
        return "UNKNOWN"


class EmailIntelligence:
    """Email metadata classifier — never reads body content (Ch 74.1)."""

    def __init__(self):
        self.events: List[EmailEvent] = []
        self.unread_count: int = 0

    def process_email_metadata(self, subject: str, sender: str) -> Optional[str]:
        event = EmailEvent(subject=subject, sender_domain=sender,
                           timestamp=datetime.now(timezone.utc))
        event.event_type = event.classify()
        if event.event_type != "UNKNOWN":
            self.events.append(event)
        return event.event_type

    def get_inbox_status(self) -> str:
        if self.unread_count >= 1000: return "crisis"
        if self.unread_count >= 500:  return "concerning"
        if self.unread_count >= 200:  return "notable"
        return "normal"


# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICATION INTELLIGENCE (Ch 79)
# ═══════════════════════════════════════════════════════════════════════════════

NOTIFICATION_CATEGORIES = {
    "CRITICAL": ["mom", "mother", "emergency", "urgent"],
    "WORK": ["slack", "jira", "linear", "github", "pr review"],
    "SOCIAL": ["whatsapp", "instagram", "twitter", "telegram"],
    "ENTERTAINMENT": ["youtube", "netflix", "spotify", "tiktok"],
}


@dataclass
class Notification:
    app: str
    title: str
    body: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    category: str = "UNKNOWN"


class NotificationQueue:
    """Hold non-critical notifications for break time (Ch 79.3)."""

    def __init__(self):
        self.held: List[Notification] = []

    def classify(self, notif: Notification) -> str:
        combined = f"{notif.app} {notif.title} {notif.body}".lower()
        for cat, keywords in NOTIFICATION_CATEGORIES.items():
            if any(k in combined for k in keywords):
                return cat
        return "UNKNOWN"

    def process(self, notif: Notification, current_state: str) -> bool:
        """Returns True if should deliver now, False if held."""
        category = self.classify(notif)
        notif.category = category
        if category == "CRITICAL":
            return True
        if category == "WORK" and "WORK" in current_state:
            return True
        if current_state in ("WORKING", "WARNING_1", "WARNING_2"):
            self.held.append(notif)
            return False
        return True

    def release_held(self) -> List[Notification]:
        released = list(self.held)
        self.held.clear()
        return released


# ═══════════════════════════════════════════════════════════════════════════════
# NOTION / LINEAR INTEGRATION (Ch 80)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TaskItem:
    title: str
    status: str  # todo | in_progress | done
    due_date: Optional[date] = None
    priority: str = "medium"
    source: str = "notion"  # notion | linear | jira


class TaskIntegration:
    """Stub for Notion / Linear / Jira task tracking."""

    def __init__(self, provider: str = "notion"):
        self.provider = provider
        self.tasks: List[TaskItem] = []

    async def get_todays_tasks(self) -> List[TaskItem]:
        today = date.today()
        return [t for t in self.tasks
                if t.status != "done" and (t.due_date is None or t.due_date <= today)]

    def get_overdue(self) -> List[TaskItem]:
        today = date.today()
        return [t for t in self.tasks
                if t.status != "done" and t.due_date and t.due_date < today]


# ═══════════════════════════════════════════════════════════════════════════════
# SPOTIFY / MUSIC INTELLIGENCE (Ch 81)
# ═══════════════════════════════════════════════════════════════════════════════

EMOTIONAL_PLAYLIST_KEYWORDS = [
    "sad", "heartbreak", "emotional", "crying", "lonely",
    "melancholy", "grief", "breakup", "missing you", "hurt",
]

FOCUS_PLAYLIST_KEYWORDS = [
    "lo-fi", "lofi", "focus", "study", "concentration",
    "ambient", "instrumental", "deep work",
]


@dataclass
class MusicContext:
    playlist_name: str = ""
    track_name: str = ""
    is_playing: bool = False

    @property
    def mood_signal(self) -> str:
        combined = f"{self.playlist_name} {self.track_name}".lower()
        if any(k in combined for k in EMOTIONAL_PLAYLIST_KEYWORDS):
            return "melancholy"
        if any(k in combined for k in FOCUS_PLAYLIST_KEYWORDS):
            return "focus"
        return "neutral"


# ═══════════════════════════════════════════════════════════════════════════════
# SMART HOME SIGNALS (Ch 75)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SmartHomeSignal:
    device: str       # bedroom_light | tv | fridge | motion_sensor
    event: str        # on | off | opened | motion | no_motion
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def hour(self) -> int:
        return self.timestamp.hour


SMART_HOME_RULES = {
    ("bedroom_light", "on", range(1, 5)): {
        "risk": 3, "msg": "Beta. Why are the lights on at this hour?",
    },
    ("tv", "on", range(9, 18)): {
        "risk": 4, "msg": "The television is on. I can see it. Turn it off.",
    },
}


def evaluate_smart_home(signal: SmartHomeSignal) -> Optional[dict]:
    for (device, event, hours), response in SMART_HOME_RULES.items():
        if signal.device == device and signal.event == event and signal.hour in hours:
            return response
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH / WEARABLE (Ch 76-77)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class HealthSnapshot:
    sleep_hours: float = 0.0
    sleep_quality: float = 0.0    # 0-1
    step_count: int = 0
    resting_hr: int = 0
    current_hr: int = 0
    last_meal_hours_ago: float = 0.0

    @property
    def stress_level(self) -> str:
        if self.resting_hr <= 0:
            return "UNKNOWN"
        elevation = self.current_hr - self.resting_hr
        if elevation > 25: return "HIGH_STRESS"
        if elevation > 15: return "MODERATE_STRESS"
        if elevation > 5:  return "MILD_STRESS"
        return "NORMAL"

    def health_nudges(self) -> List[str]:
        nudges = []
        if self.sleep_hours > 0 and self.sleep_hours < 6:
            nudges.append(f"{self.sleep_hours:.1f} hours of sleep. Not enough.")
        if self.step_count < 2000 and self.step_count > 0:
            nudges.append("Move. You have barely walked today.")
        if self.last_meal_hours_ago > 6:
            nudges.append("Beta, have you eaten today? Actually eaten?")
        return nudges


# ═══════════════════════════════════════════════════════════════════════════════
# CONTACT AWARENESS (Ch 78)
# ═══════════════════════════════════════════════════════════════════════════════

class ContactCategory:
    REAL_MOM = "real_mom"
    CLOSE_FAMILY = "close_family"
    DISTRACTION_FRIEND = "distraction_friend"
    WORK = "work"
    EX = "ex"
    UNKNOWN = "unknown"


@dataclass
class Contact:
    name: str
    category: str = ContactCategory.UNKNOWN


EX_PROTOCOL_DIALOGUE = {
    "profile_3x": "Beta. We are not doing this today.",
    "typing_11pm": "Beta. Put. The phone. Down. Whatever you are about to send — don't.",
    "message_2am": "Okay. It has been sent. I cannot unsend it. But I can be here when you need me.",
    "call_2am": "This is not a great idea, beta. I am just saying.",
}


# ═══════════════════════════════════════════════════════════════════════════════
# LIFE CONTEXT ENGINE (Ch 83)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LifeContext:
    calendar_pressure: float = 0.0    # 0-1 (deadline proximity)
    email_sentiment: str = "neutral"  # positive | negative | neutral
    music_mood: str = "neutral"       # positive | melancholy | neutral
    health_status: str = "unknown"    # good | tired | stressed | unknown
    contact_recent: str = "none"      # family | friend | ex | none
    smart_home_flags: List[str] = field(default_factory=list)

    def recommended_mode(self) -> str:
        """Determine recommended Amma mode from combined signals (Ch 83.2)."""
        if self.health_status == "crisis":
            return "CRISIS"

        distress_score = sum([
            1 if self.email_sentiment == "negative" else 0,
            1 if self.music_mood == "melancholy" else 0,
            1 if self.health_status == "stressed" else 0,
            1 if self.contact_recent == "ex" else 0,
        ])
        if distress_score >= 2:
            return "SUPPORT"

        pressure_score = sum([
            1 if self.calendar_pressure > 0.7 else 0,
            1 if self.health_status == "tired" else 0,
        ])
        if pressure_score >= 2:
            return "GUARD_STRICT"

        return "GUARD"
