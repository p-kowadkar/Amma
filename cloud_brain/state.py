"""
Cloud Brain State Manager — Ch 6.4
Redis-backed unified session state for cross-device Amma.
Falls back to in-memory dict when Redis is unavailable.
"""
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any

SESSION_TTL = 86400  # 24 hours
KEY_PREFIX = "amma:session"


def _session_key(user_id: str) -> str:
    return f"{KEY_PREFIX}:{user_id}"


# Default state schema per spec Ch 6.4
def default_session_state() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "timepass_seconds": 0,
        "work_seconds": 0,
        "work_streak_seconds": 0,
        "warning_level": 0,
        "in_break": False,
        "break_start_ts": None,
        "last_classification": "WORK",
        "last_update_ts": now,
        "pattern_counts": {},
        "pattern_time": {},
        "session_rulings": {},
        "trust_score": 1.0,
        "excuse_log": [],
        "active_devices": [],
        "phone_risk_level": 0,
        "laptop_classification": "WORK",
        "phone_classification": "UNKNOWN",
        "current_mode": "GUARD",
        "last_intervention_ts": None,
        "last_intervention_level": 0,
        "session_start_ts": now,
        "peak_warning_level": 0,
        "longest_work_streak_seconds": 0,
        "nuclear_count": 0,
    }


class AmmaStateManager:
    """
    Manages per-user session state.
    Uses Redis when available, falls back to in-memory dict.
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._memory: Dict[str, dict] = {}  # Fallback
        self._devices: Dict[str, Dict[str, Any]] = {}  # user_id → {device → websocket}

    @property
    def uses_redis(self) -> bool:
        return self._redis is not None

    async def get_state(self, user_id: str) -> dict:
        if self._redis:
            raw = await self._redis.get(_session_key(user_id))
            if raw:
                return json.loads(raw)
        if user_id in self._memory:
            return self._memory[user_id]
        # Initialize
        state = default_session_state()
        await self.set_state(user_id, state)
        return state

    async def set_state(self, user_id: str, state: dict):
        if self._redis:
            await self._redis.setex(
                _session_key(user_id), SESSION_TTL, json.dumps(state)
            )
        else:
            self._memory[user_id] = state

    async def update_field(self, user_id: str, field: str, value: Any):
        state = await self.get_state(user_id)
        state[field] = value
        state["last_update_ts"] = datetime.now(timezone.utc).isoformat()
        await self.set_state(user_id, state)

    async def update_classification(self, user_id: str, device: str, data: dict):
        """Process an OBSERVATION event — update state with new classification."""
        state = await self.get_state(user_id)
        classification = data.get("classification", "GREY")

        if device == "laptop":
            state["laptop_classification"] = classification
        elif device == "phone":
            state["phone_classification"] = classification

        state["last_classification"] = classification
        state["last_update_ts"] = datetime.now(timezone.utc).isoformat()

        # Track pattern counts
        app = data.get("dominant_app", "")
        if classification == "TIMEPASS" and app:
            key = app.lower().strip().replace(" ", "-")
            counts = state.get("pattern_counts", {})
            counts[key] = counts.get(key, 0) + 1
            state["pattern_counts"] = counts

        await self.set_state(user_id, state)
        return state

    async def update_phone_risk(self, user_id: str, risk_level: int, category: str):
        """Process a PHONE_SIGNAL event."""
        state = await self.get_state(user_id)
        state["phone_risk_level"] = risk_level
        state["phone_classification"] = category
        state["last_update_ts"] = datetime.now(timezone.utc).isoformat()
        await self.set_state(user_id, state)
        return state

    async def check_cross_device(self, user_id: str) -> Optional[dict]:
        """Cross-device contradiction detection (Ch 6.5)."""
        state = await self.get_state(user_id)
        laptop = state.get("laptop_classification", "UNKNOWN")
        phone_risk = state.get("phone_risk_level", 0)

        # Laptop says WORK, phone says high-risk
        if laptop == "WORK" and phone_risk >= 3:
            return {
                "type": "CONTRADICTION",
                "message": (
                    "Beta. Your laptop says you are working. "
                    "Your phone disagrees. "
                    "Would you like to tell me what is actually happening?"
                ),
            }

        # Laptop dark, phone high activity
        if laptop == "UNKNOWN" and phone_risk >= 4:
            return {
                "type": "BLIND_SPOT_CAUGHT",
                "message": (
                    "Beta, your laptop screen went off. "
                    "Your phone is telling me a story right now. "
                    "I am listening to your phone."
                ),
            }

        return None

    async def register_device(self, user_id: str, device: str, websocket=None):
        state = await self.get_state(user_id)
        devices = state.get("active_devices", [])
        if device not in devices:
            devices.append(device)
            state["active_devices"] = devices
            await self.set_state(user_id, state)
        # Track websocket for broadcasting
        if user_id not in self._devices:
            self._devices[user_id] = {}
        self._devices[user_id][device] = websocket

    async def unregister_device(self, user_id: str, device: str):
        state = await self.get_state(user_id)
        devices = state.get("active_devices", [])
        if device in devices:
            devices.remove(device)
            state["active_devices"] = devices
            await self.set_state(user_id, state)
        if user_id in self._devices:
            self._devices[user_id].pop(device, None)

    async def get_device_websocket(self, user_id: str, device: str):
        return self._devices.get(user_id, {}).get(device)

    async def save_for_lid_close(self, user_id: str):
        """Persist state before laptop lid close / sleep."""
        state = await self.get_state(user_id)
        state["_saved_for_resume"] = True
        await self.set_state(user_id, state)

    async def restore_after_resume(self, user_id: str) -> dict:
        """Restore state after laptop lid open / wake."""
        state = await self.get_state(user_id)
        state.pop("_saved_for_resume", None)
        state["last_update_ts"] = datetime.now(timezone.utc).isoformat()
        await self.set_state(user_id, state)
        return state

    async def delete_session(self, user_id: str):
        if self._redis:
            await self._redis.delete(_session_key(user_id))
        self._memory.pop(user_id, None)
        self._devices.pop(user_id, None)
