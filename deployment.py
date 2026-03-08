"""
Deployment, Onboarding & Observability — Ch 127-133
Full config schema, onboarding flow, structured logging, fallback classification.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, List
import json
import logging


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG SCHEMA (Ch 133)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class UserConfig:
    first_name: str = "User"
    formal_name: str = "User"
    nickname: str = "Beta"
    full_name: str = ""        # Nuclear trigger
    endearment: str = "beta"


@dataclass
class PersonalityConfig:
    archetype: str = "classic"    # classic | modern | anxious | competitive | philosopher | dadi
    strictness: int = 8           # 1-10
    warmth: int = 7
    guilt_trips: int = 7
    patience_minutes: int = 45    # Level 1 threshold
    humor: int = 5
    cultural_intensity: int = 9


@dataclass
class LanguageConfig:
    primary: List[str] = field(default_factory=lambda: ["English"])
    scold_language: str = "English"
    support_language: str = "English"
    technical_language: str = "English"
    default: str = "English"
    cultural_pack: str = "south-indian-english"


@dataclass
class ThresholdConfig:
    level_1_minutes: int = 45
    level_2_minutes: int = 60
    level_3_minutes: int = 75
    level_4_minutes: int = 90
    level_5_minutes: int = 105
    reset_minutes: int = 120
    break_max_minutes: int = 75


@dataclass
class AudioConfig:
    voice: str = "Aoede"       # Aoede | Charon | Fenrir | Kore | Puck
    volume_normal: float = 0.70
    volume_scream: float = 1.00


@dataclass
class IntegrationsConfig:
    google_calendar: bool = False
    gmail: bool = False
    spotify: bool = False
    notion: bool = False
    linear: bool = False
    smart_home: bool = False
    wearable: str = "none"  # apple_watch | fitbit | garmin | none


@dataclass
class PrivacyConfig:
    exclude_apps: List[str] = field(default_factory=lambda: [
        "1Password", "Bitwarden", "Signal",
    ])
    exclude_windows_containing: List[str] = field(default_factory=lambda: [
        "bank", "password",
    ])
    camera_posture_detection: bool = False


@dataclass
class CloudConfig:
    mode: str = "managed"    # managed | self_hosted
    api_key: str = ""


@dataclass
class AmmaFullConfig:
    """Master configuration schema (Ch 133.1)."""
    user: UserConfig = field(default_factory=UserConfig)
    personality: PersonalityConfig = field(default_factory=PersonalityConfig)
    languages: LanguageConfig = field(default_factory=LanguageConfig)
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    integrations: IntegrationsConfig = field(default_factory=IntegrationsConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)
    cloud: CloudConfig = field(default_factory=CloudConfig)


# ═══════════════════════════════════════════════════════════════════════════════
# ONBOARDING (Ch 127)
# ═══════════════════════════════════════════════════════════════════════════════

ONBOARDING_STEPS = [
    "install_client",
    "first_words",           # Amma speaks immediately — no tutorial
    "setup_interview",       # 5-7 min conversation
    "calibration_summary",   # "So. You are Pranav..."
    "first_classification",  # 30s silent calibration
    "first_intervention",    # Or first radio praise
    "session_debrief",       # End of first session
]


@dataclass
class OnboardingState:
    user_id: str
    current_step: int = 0
    is_first_session: bool = True
    completed: bool = False

    @property
    def step_name(self) -> str:
        if self.current_step < len(ONBOARDING_STEPS):
            return ONBOARDING_STEPS[self.current_step]
        return "complete"

    def advance(self):
        self.current_step += 1
        if self.current_step >= len(ONBOARDING_STEPS):
            self.completed = True


# First session modifier (Ch 127.3)
def first_session_adjustments(config: AmmaFullConfig) -> dict:
    """Returns temporary overrides for first session."""
    return {
        "strictness_cap": min(config.personality.strictness, 6),
        "extra_patience_minutes": 15,
        "note": "This is our first session. I am watching and learning. "
                "Do not think this gentleness will last.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STRUCTURED LOGGING (Ch 130.2)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AmmaLogEvent:
    """Structured log entry — no raw screen content, URLs, or behavioral details."""
    timestamp: str = ""
    user_id: str = ""           # Hashed for PII logs
    session_id: str = ""
    event_type: str = ""        # CLASSIFICATION | INTERVENTION | STATE_CHANGE | CRISIS
    classification: Optional[str] = None  # WORK | GREY | TIMEPASS | BREAK
    confidence: Optional[float] = None
    timepass_total_seconds: int = 0
    warning_level: int = 0
    intervention_level: Optional[int] = None
    latency_ms: int = 0
    llm_model: str = ""
    device: str = "laptop"
    error: Optional[str] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_json(self) -> str:
        return json.dumps({
            k: v for k, v in self.__dict__.items() if v is not None
        })


class AmmaLogger:
    """Structured JSON logger for Amma events."""

    def __init__(self, name: str = "amma"):
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log_event(self, event: AmmaLogEvent):
        self.logger.info(event.to_json())

    def log_classification(self, user_id: str, session_id: str,
                           classification: str, confidence: float, latency_ms: int):
        self.log_event(AmmaLogEvent(
            user_id=user_id, session_id=session_id,
            event_type="CLASSIFICATION", classification=classification,
            confidence=confidence, latency_ms=latency_ms,
        ))

    def log_intervention(self, user_id: str, session_id: str,
                         level: int, timepass_seconds: int):
        self.log_event(AmmaLogEvent(
            user_id=user_id, session_id=session_id,
            event_type="INTERVENTION", intervention_level=level,
            timepass_total_seconds=timepass_seconds,
        ))

    def log_crisis(self, user_id: str, session_id: str, trigger: str):
        self.log_event(AmmaLogEvent(
            user_id=user_id, session_id=session_id,
            event_type="CRISIS", error=trigger,
        ))


# ═══════════════════════════════════════════════════════════════════════════════
# FALLBACK CLASSIFICATION (Ch 131.3)
# ═══════════════════════════════════════════════════════════════════════════════

# Process name → classification lookup
PROCESS_RISK_MAP = {
    "code": "WORK", "Code": "WORK", "code.exe": "WORK",
    "pycharm": "WORK", "pycharm64.exe": "WORK",
    "idea": "WORK", "idea64.exe": "WORK",
    "chrome": "GREY", "chrome.exe": "GREY",
    "firefox": "GREY", "firefox.exe": "GREY",
    "slack": "WORK", "Slack.exe": "WORK",
    "discord": "GREY", "Discord.exe": "GREY",
    "spotify": "GREY", "Spotify.exe": "GREY",
    "netflix": "TIMEPASS",
}

# Window title keywords → classification
WINDOW_TITLE_RULES = {
    "WORK": ["VS Code", "PyCharm", "IntelliJ", "Terminal", "cmd", "PowerShell",
             "Stack Overflow", "GitHub", "gitlab", "Linear", "Jira"],
    "TIMEPASS": ["Netflix", "Tinder", "Instagram", "TikTok", "Attack on Titan",
                 "anime", "Grand Theft Auto"],
}


def fallback_classify_window_title(title: str) -> str:
    """Rule-based classification from window title only (Ch 131.3)."""
    title_lower = title.lower()
    for classification, keywords in WINDOW_TITLE_RULES.items():
        if any(k.lower() in title_lower for k in keywords):
            return classification
    return "GREY"


def fallback_classify_process(process_name: str) -> str:
    return PROCESS_RISK_MAP.get(process_name, "GREY")


def fallback_classify_time(hour: int) -> str:
    """Last resort: time-based assumption."""
    return "WORK" if 9 <= hour <= 18 else "GREY"
