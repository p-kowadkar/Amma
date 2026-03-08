"""
Phone Client Protocol — Ch 43-52
Cross-device event schema, privacy-safe data flow, contradiction detection.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List
from behavioral_signals import Signal, calculate_risk_score, classify_risk_category


# ── Phone event types (Ch 43.2) ─────────────────────────────────────────────

class PhoneEventType:
    HEARTBEAT = "HEARTBEAT"            # Regular 60s check-in
    RISK_UPDATE = "RISK_UPDATE"        # Risk score changed significantly
    NUCLEAR_TRIGGER = "NUCLEAR_TRIGGER"  # Adult content detected → immediate
    LOCATION_CHANGE = "LOCATION_CHANGE"  # Location type changed
    DEVICE_STATE = "DEVICE_STATE"       # Screen on/off, battery, headphones


@dataclass
class PhoneEvent:
    event_type: str
    risk_level: int          # 0-5, NEVER raw signals
    category: str            # social | adult | gaming | entertainment | other
    location_type: str = "unknown"  # home | office | gym | commute | unknown
    timestamp: str = ""
    device_state: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_safe_dict(self) -> dict:
        """Privacy-safe payload — NEVER includes raw signals, URLs, app names."""
        return {
            "event_type": self.event_type,
            "risk_level": self.risk_level,
            "category": self.category,
            "location_type": self.location_type,
            "timestamp": self.timestamp,
        }


# ── App risk map (Ch 44.3) ─ package names → risk/category ──────────────────

APP_RISK_MAP = {
    # Dating
    "com.tinder": {"risk": 4, "category": "social"},
    "com.bumble.app": {"risk": 4, "category": "social"},
    # Streaming
    "com.netflix.mediaclient": {"risk": 4, "category": "entertainment"},
    "com.hotstar": {"risk": 4, "category": "entertainment"},
    "com.disney.disneyplus": {"risk": 4, "category": "entertainment"},
    # Social
    "com.instagram.android": {"risk": 3, "category": "social"},
    "com.twitter.android": {"risk": 2, "category": "social"},
    "com.snapchat.android": {"risk": 3, "category": "social"},
    "com.zhiliaoapp.musically": {"risk": 4, "category": "social"},  # TikTok
    # Gaming
    "com.mojang.minecraftpe": {"risk": 2, "category": "gaming"},
    # Work — zero risk
    "com.google.android.gm": {"risk": 0, "category": "work"},
    "com.slack": {"risk": 0, "category": "work"},
    "com.github.android": {"risk": 0, "category": "work"},
}


def classify_app(package_name: str) -> dict:
    """On-device app classification — raw package name NEVER transmitted."""
    return APP_RISK_MAP.get(package_name, {"risk": 1, "category": "unknown"})


# ── Domain classification (Ch 48.2) ─────────────────────────────────────────

DOMAIN_CATEGORIES = {
    "pornhub.com": {"category": "adult", "risk": 5},
    "xvideos.com": {"category": "adult", "risk": 5},
    "netflix.com": {"category": "entertainment", "risk": 4},
    "youtube.com": {"category": "entertainment", "risk": 2},
    "instagram.com": {"category": "social", "risk": 3},
    "twitter.com": {"category": "social", "risk": 2},
    "reddit.com": {"category": "social", "risk": 2},
    "github.com": {"category": "work", "risk": 0},
    "stackoverflow.com": {"category": "work", "risk": 0},
    "linear.app": {"category": "work", "risk": 0},
}


def classify_url(url: str) -> dict:
    """On-device URL classification — raw URL NEVER transmitted."""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).hostname or ""
        domain = domain.replace("www.", "")
        return DOMAIN_CATEGORIES.get(domain, {"category": "unknown", "risk": 1})
    except Exception:
        return {"category": "unknown", "risk": 0}


# ── Location classification (Ch 49, 52.3) ───────────────────────────────────

@dataclass
class LocationProfile:
    home_coords: Optional[tuple] = None   # (lat, lon)
    office_coords: Optional[tuple] = None
    radius_m: float = 100.0


def classify_location(lat: float, lon: float, profile: LocationProfile) -> str:
    """On-device location classification — raw GPS NEVER transmitted."""
    import math

    def distance(c1, c2):
        """Haversine approx in meters."""
        R = 6_371_000
        lat1, lon1 = math.radians(c1[0]), math.radians(c1[1])
        lat2, lon2 = math.radians(c2[0]), math.radians(c2[1])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    coords = (lat, lon)
    if profile.home_coords and distance(coords, profile.home_coords) < 50:
        return "home"
    if profile.office_coords and distance(coords, profile.office_coords) < profile.radius_m:
        return "office"
    return "unknown"


# ── Cross-device correlation (Ch 51) ────────────────────────────────────────

@dataclass
class CrossDeviceState:
    laptop_classification: str = "UNKNOWN"
    phone_risk_level: int = 0
    phone_category: str = "other"
    laptop_last_update: str = ""
    phone_last_update: str = ""


def detect_contradictions(state: CrossDeviceState) -> List[dict]:
    """Detect laptop/phone contradictions (Ch 6.4, 51.1)."""
    contradictions = []

    if state.laptop_classification == "WORK" and state.phone_risk_level >= 3:
        contradictions.append({
            "type": "WORK_PHONE_CONTRADICTION",
            "message": (
                "Beta. Your laptop says you are working. "
                "Your phone has something to say about that. "
                "Would you like to tell me what is actually going on?"
            ),
        })

    if state.laptop_classification == "UNKNOWN" and state.phone_risk_level >= 4:
        contradictions.append({
            "type": "BLIND_SPOT_CAUGHT",
            "message": (
                "Interesting. Your laptop screen went off "
                "at exactly the same time your phone got very busy. "
                "I am not making any accusations. "
                "I am just noting the timing."
            ),
        })

    return contradictions
