import mss
import asyncio
import base64
import io
from PIL import Image
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional
import platform

PRIVACY_EXCLUSIONS = [
    "1password", "bitwarden", "keepass", "keychain",
    "signal", "banking", "bank", "private browsing",
]

def get_active_window_title() -> str:
    system = platform.system()
    try:
        if system == "Windows":
            import win32gui
            return win32gui.GetWindowText(win32gui.GetForegroundWindow())
        elif system == "Darwin":
            from AppKit import NSWorkspace
            app = NSWorkspace.sharedWorkspace().activeApplication()
            return app.get("NSApplicationName", "Unknown")
        elif system == "Linux":
            import subprocess
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True
            )
            return result.stdout.strip() if result.returncode == 0 else "Unknown"
    except Exception:
        pass
    return "Unknown"

def get_active_process_name() -> str:
    try:
        import psutil
        import subprocess
        system = platform.system()
        if system == "Windows":
            import win32process, win32gui
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            return proc.name()
        elif system == "Darwin":
            from AppKit import NSWorkspace
            app = NSWorkspace.sharedWorkspace().activeApplication()
            return app.get("NSApplicationName", "Unknown")
        elif system == "Linux":
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowpid"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                pid = int(result.stdout.strip())
                proc = psutil.Process(pid)
                return proc.name()
    except Exception:
        pass
    return "Unknown"

def is_excluded(window_title: str) -> bool:
    title_lower = window_title.lower()
    return any(exc in title_lower for exc in PRIVACY_EXCLUSIONS)

def resize_for_gemini(img: Image.Image, max_width: int = 1280) -> Image.Image:
    if img.width > max_width:
        ratio = max_width / img.width
        new_size = (max_width, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    return img

def encode_jpeg(img: Image.Image, quality: int = 85) -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode()

@dataclass
class ScreenFrame:
    image_b64: str
    timestamp: str
    window_title: str
    window_process: str
    is_private: bool = False

async def vision_loop(vision_queue: asyncio.Queue, interval: float = 5.0,
                      monitor_index: int = 0):
    """Capture screen every `interval` seconds and push to queue.

    Args:
        monitor_index: 0 = all monitors combined (default), 1+ = specific monitor.
    """
    with mss.mss() as sct:
        if monitor_index < 0 or monitor_index >= len(sct.monitors):
            print(f"[Vision] Monitor {monitor_index} not found, using 0 (all).")
            monitor_index = 0
        monitor = sct.monitors[monitor_index]
        while True:
            start = datetime.now(timezone.utc)
            window_title = get_active_window_title()
            process_name = get_active_process_name()

            if is_excluded(window_title):
                await vision_queue.put(ScreenFrame(
                    image_b64="",
                    timestamp=start.isoformat(),
                    window_title=window_title,
                    window_process=process_name,
                    is_private=True,
                ))
            else:
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                img = resize_for_gemini(img)
                img_b64 = encode_jpeg(img)
                await vision_queue.put(ScreenFrame(
                    image_b64=img_b64,
                    timestamp=start.isoformat(),
                    window_title=window_title,
                    window_process=process_name,
                ))

            elapsed = (datetime.now(timezone.utc) - start).total_seconds()
            await asyncio.sleep(max(0, interval - elapsed))