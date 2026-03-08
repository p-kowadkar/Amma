"""
Cloud Brain Event Protocol — Ch 4.2
Defines all message types between clients and the Cloud Brain.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any, Dict


class EventType(str, Enum):
    # Client → Brain
    OBSERVATION = "OBSERVATION"
    USER_COMMAND = "USER_COMMAND"
    PHONE_SIGNAL = "PHONE_SIGNAL"
    HEARTBEAT = "HEARTBEAT"
    # Brain → Client
    VOICE_COMMAND = "VOICE_COMMAND"
    STATE_UPDATE = "STATE_UPDATE"
    MODE_CHANGE = "MODE_CHANGE"
    # Brain → Brain (internal)
    CROSS_DEVICE = "CROSS_DEVICE"


class DeviceType(str, Enum):
    LAPTOP = "laptop"
    PHONE = "phone"
    PARENT_PORTAL = "parent_portal"


@dataclass
class Event:
    type: EventType
    device: DeviceType
    user_id: str
    timestamp: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = self.type.value
        d["device"] = self.device.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Event":
        return cls(
            type=EventType(d["type"]),
            device=DeviceType(d.get("device", "laptop")),
            user_id=d.get("user_id", ""),
            timestamp=d.get("timestamp", ""),
            data=d.get("data", {}),
        )


# ── Convenience constructors ────────────────────────────────────────────────

def observation_event(user_id: str, device: DeviceType,
                      classification: str, confidence: float,
                      dominant_app: str = "", nuclear: bool = False) -> Event:
    return Event(
        type=EventType.OBSERVATION,
        device=device,
        user_id=user_id,
        data={
            "classification": classification,
            "confidence": confidence,
            "dominant_app": dominant_app,
            "nuclear": nuclear,
        },
    )


def phone_signal_event(user_id: str, risk_level: int,
                       category: str = "other") -> Event:
    """Phone sends ONLY risk_level (0-5), category, timestamp. Never raw signals."""
    return Event(
        type=EventType.PHONE_SIGNAL,
        device=DeviceType.PHONE,
        user_id=user_id,
        data={
            "risk_level": min(max(risk_level, 0), 5),
            "category": category,  # social | adult | gaming | other
        },
    )


def voice_command_event(user_id: str, target_device: DeviceType,
                        text: str, volume: float = 0.70,
                        intervention_type: str = "") -> Event:
    return Event(
        type=EventType.VOICE_COMMAND,
        device=target_device,
        user_id=user_id,
        data={
            "text": text,
            "volume": volume,
            "intervention_type": intervention_type,
        },
    )


def state_update_event(user_id: str, state_data: dict) -> Event:
    return Event(
        type=EventType.STATE_UPDATE,
        device=DeviceType.LAPTOP,  # broadcast
        user_id=user_id,
        data=state_data,
    )
