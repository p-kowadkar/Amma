"""
Cloud Brain FastAPI Server — Ch 6.2
WebSocket server coordinating all Amma clients.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Optional

from cloud_brain.state import AmmaStateManager
from cloud_brain.protocol import (
    EventType, Event, voice_command_event, state_update_event,
)

app = FastAPI(title="Amma Cloud Brain", version="0.1.0")
state_manager = AmmaStateManager()  # In-memory by default; pass Redis client for production


@app.get("/health")
async def health():
    return {"status": "ok", "brain": "awake"}


@app.websocket("/ws/{user_id}/{device}")
async def amma_socket(websocket: WebSocket, user_id: str, device: str):
    await websocket.accept()
    await state_manager.register_device(user_id, device, websocket)
    print(f"[Brain] Device connected: {user_id}/{device}")

    try:
        while True:
            raw = await websocket.receive_json()
            event = Event.from_dict(raw)
            event.user_id = user_id  # Enforce from URL
            response = await handle_event(user_id, device, event)
            if response:
                await websocket.send_json(response.to_dict())
    except WebSocketDisconnect:
        print(f"[Brain] Device disconnected: {user_id}/{device}")
    except Exception as e:
        print(f"[Brain] Error for {user_id}/{device}: {e}")
    finally:
        await state_manager.unregister_device(user_id, device)


async def handle_event(user_id: str, device: str, event: Event) -> Optional[Event]:
    """Route events to appropriate handlers. Returns response event or None."""

    if event.type == EventType.OBSERVATION:
        await state_manager.update_classification(user_id, device, event.data)

        # Cross-device contradiction check
        contradiction = await state_manager.check_cross_device(user_id)
        if contradiction:
            return voice_command_event(
                user_id, event.device,
                text=contradiction["message"],
                volume=0.80,
                intervention_type=contradiction["type"],
            )

        # Return current state for client sync
        current = await state_manager.get_state(user_id)
        return state_update_event(user_id, current)

    elif event.type == EventType.PHONE_SIGNAL:
        risk = event.data.get("risk_level", 0)
        category = event.data.get("category", "other")
        await state_manager.update_phone_risk(user_id, risk, category)

        # Cross-device check after phone update
        contradiction = await state_manager.check_cross_device(user_id)
        if contradiction:
            # Send voice command to LAPTOP (phone caught you)
            laptop_ws = await state_manager.get_device_websocket(user_id, "laptop")
            if laptop_ws:
                try:
                    cmd = voice_command_event(
                        user_id, event.device,
                        text=contradiction["message"],
                        volume=0.80,
                        intervention_type=contradiction["type"],
                    )
                    await laptop_ws.send_json(cmd.to_dict())
                except Exception:
                    pass
        return None

    elif event.type == EventType.USER_COMMAND:
        command = event.data.get("command", "")
        return await handle_user_command(user_id, device, command, event.data)

    elif event.type == EventType.HEARTBEAT:
        return None

    return None


async def handle_user_command(user_id: str, device: str,
                              command: str, data: dict) -> Optional[Event]:
    """Handle user commands like break, context declaration, etc."""
    if command == "break":
        await state_manager.update_field(user_id, "in_break", True)
        return voice_command_event(
            user_id, EventType.VOICE_COMMAND,
            text="Okay beta. Take your break. I will be here.",
            volume=0.60,
        )
    elif command == "back":
        await state_manager.update_field(user_id, "in_break", False)
        return voice_command_event(
            user_id, EventType.VOICE_COMMAND,
            text="Welcome back. Let's go.",
            volume=0.65,
        )
    elif command == "declare_work":
        app_name = data.get("app", "")
        if app_name:
            state = await state_manager.get_state(user_id)
            rulings = state.get("session_rulings", {})
            rulings[app_name.lower().replace(" ", "-")] = "WORK"
            state["session_rulings"] = rulings
            await state_manager.set_state(user_id, state)
    elif command == "lid_close":
        await state_manager.save_for_lid_close(user_id)
    elif command == "lid_open":
        await state_manager.restore_after_resume(user_id)
        return voice_command_event(
            user_id, EventType.VOICE_COMMAND,
            text="Back. Where were we.",
            volume=0.60,
        )
    return None


def create_app(redis_client=None) -> FastAPI:
    """Factory for creating app with optional Redis."""
    global state_manager
    state_manager = AmmaStateManager(redis_client=redis_client)
    return app
