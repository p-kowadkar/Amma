"""
Amma Overlay — Glass UI (Ch 2.4 — “Always Present”)

PyQt6 frameless, always-on-top glass widget.
Inspired by Cluely / Glass: translucent, floating, beautiful.
No stealth — Amma is visible. She is your mother, not your accomplice.

Windows 11/10: real acrylic blur via DwmSetWindowAttribute.
Fallback: semi-transparent dark overlay.
"""
import ctypes
import platform
import queue
import random
import threading
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, QThread, pyqtSignal
from PyQt6.QtGui import (
    QColor, QPainter, QPainterPath, QFont, QFontMetrics,
    QPen, QBrush, QLinearGradient,
)
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel

# Fallback to tkinter if PyQt6 not available
try:
    import tkinter as tk  # noqa: F401  — kept for import guard only
except ImportError:
    pass

# ── Palette ─────────────────────────────────────────────────────────────────────
C_BG        = QColor(10, 10, 16, 220)      # Near-black glass
C_BORDER    = QColor(255, 255, 255, 18)    # Subtle white border
C_ACCENT    = QColor(255, 136, 0)          # Amma orange
C_WORK      = QColor(76, 195, 80)          # Green
C_TIMEPASS  = QColor(244, 67, 54)          # Red
C_GREY      = QColor(160, 160, 170)        # Neutral grey
C_TEXT      = QColor(240, 240, 240)        # Almost white
C_MUTED     = QColor(140, 140, 155)        # Dimmed text
C_WARNING   = [                            # L0→L6
    QColor(76,  175, 80),    # L0 green
    QColor(255, 235, 59),    # L1 yellow
    QColor(255, 152,  0),    # L2 orange
    QColor(244,  67, 54),    # L3 red
    QColor(198,  40, 40),    # L4 dark red
    QColor(183,  28, 28),    # L5 darker red
    QColor(136,   0,  0),    # L6 nuclear
]
CORNER_R    = 14                           # Rounded corner radius
WIDGET_W    = 280
WIDGET_H    = 210


# ── Windows acrylic/blur helpers ───────────────────────────────────────────────────
def _apply_windows_blur(hwnd: int):
    """Apply real OS-level blur behind the window (Windows 10/11)."""
    if platform.system() != "Windows":
        return
    try:
        # Windows 11 22H2+ — DWMWA_SYSTEMBACKDROP_TYPE = 38, acrylic = 3
        DWMWA_SYSTEMBACKDROP_TYPE = 38
        DWMSBT_ACRYLIC = 3
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(ctypes.c_int(DWMSBT_ACRYLIC)),
            ctypes.sizeof(ctypes.c_int),
        )
        return
    except Exception:
        pass
    try:
        # Windows 10 fallback — DwmEnableBlurBehindWindow
        class _DWM_BLURBEHIND(ctypes.Structure):
            _fields_ = [
                ("dwFlags",                ctypes.c_uint),
                ("fEnable",               ctypes.c_bool),
                ("hRgnBlur",              ctypes.c_void_p),
                ("fTransitionOnMaximized",ctypes.c_bool),
            ]
        bb = _DWM_BLURBEHIND(dwFlags=1, fEnable=True, hRgnBlur=None)
        ctypes.windll.dwmapi.DwmEnableBlurBehindWindow(hwnd, ctypes.byref(bb))
    except Exception:
        pass  # Graceful degradation on unsupported Windows


# ── Glass widget ───────────────────────────────────────────────────────────────────────
class GlassWidget(QWidget):
    """The floating glass overlay window."""

    def __init__(self):
        super().__init__()
        self._classification = "WORK"
        self._warning_level   = 0
        self._work_min        = 0
        self._timepass_min    = 0
        self._in_break        = False
        self._last_line       = "Amma is watching."
        self._mode            = "GUARD"
        self._drag_pos: Optional[QPoint] = None

        self._setup_window()
        self._apply_blur()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool                 # No taskbar entry
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFixedSize(WIDGET_W, WIDGET_H)
        # Position: top-right corner (adjust once screen dims are known)
        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            self.move(sg.right() - WIDGET_W - 24, sg.top() + 40)

    def _apply_blur(self):
        hwnd = int(self.winId())
        _apply_windows_blur(hwnd)

    # ── State updates (called from main thread via queue) ──────────────────────────────
    def apply_state(self, state: dict):
        self._classification = state.get("classification", self._classification)
        self._warning_level  = state.get("warning_level",  self._warning_level)
        self._work_min       = state.get("work_min",       self._work_min)
        self._timepass_min   = state.get("timepass_min",   self._timepass_min)
        self._in_break       = state.get("in_break",       self._in_break)
        self._mode           = state.get("mode",           self._mode)
        if "last_line" in state and state["last_line"]:
            self._last_line = state["last_line"]
        self.update()  # Trigger repaint

    # ── Painting ────────────────────────────────────────────────────────────────────────────────
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        rect = self.rect()

        # ─ Background pill ──────────────────────────────────────────────────────────────
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, CORNER_R, CORNER_R)
        p.setClipPath(path)
        p.fillPath(path, QBrush(C_BG))

        # ─ Top accent bar (warning level color, 3px) ───────────────────────────────────
        wl = min(self._warning_level, len(C_WARNING) - 1)
        bar_color = C_WARNING[wl]
        bar_path = QPainterPath()
        bar_path.addRoundedRect(0, 0, w, 4, CORNER_R, CORNER_R)
        p.fillPath(bar_path, QBrush(bar_color))

        # ─ Border ─────────────────────────────────────────────────────────────────────────
        border_path = QPainterPath()
        border_path.addRoundedRect(0.5, 0.5, w - 1, h - 1, CORNER_R, CORNER_R)
        p.setPen(QPen(C_BORDER, 1))
        p.drawPath(border_path)
        p.setPen(Qt.PenStyle.NoPen)

        # ─ Header: “Amma” + mode pill ────────────────────────────────────────────────────
        y = 18
        font_title = QFont("Segoe UI", 11, QFont.Weight.Bold)
        p.setFont(font_title)
        p.setPen(QPen(C_ACCENT))
        p.drawText(16, y, "Amma \u0905\u092e\u094d\u092e\u093e")

        # Mode pill (top-right)
        mode_text = "BREAK" if self._in_break else self._mode
        mode_color = QColor(255, 152, 0, 160) if self._in_break else QColor(255, 255, 255, 18)
        font_small = QFont("Segoe UI", 7, QFont.Weight.Bold)
        fm = QFontMetrics(font_small)
        pill_w = fm.horizontalAdvance(mode_text) + 16
        pill_x = w - pill_w - 12
        pill_rect = QPainterPath()
        pill_rect.addRoundedRect(pill_x, y - 11, pill_w, 16, 8, 8)
        p.fillPath(pill_rect, QBrush(mode_color))
        p.setFont(font_small)
        p.setPen(QPen(C_TEXT))
        p.drawText(pill_x + 8, y, mode_text)

        # ─ Separator line ───────────────────────────────────────────────────────────────
        y += 14
        p.setPen(QPen(C_BORDER))
        p.drawLine(14, y, w - 14, y)

        # ─ Classification + Warning Level ──────────────────────────────────────────────
        y += 22
        cls = self._classification
        cls_color = (
            C_WORK      if cls == "WORK"     else
            C_TIMEPASS  if cls == "TIMEPASS" else
            C_GREY
        )
        # Big classification text
        font_cls = QFont("Segoe UI", 18, QFont.Weight.Bold)
        p.setFont(font_cls)
        p.setPen(QPen(cls_color))
        p.drawText(16, y, cls)

        # Warning level badge (right-aligned)
        wl_color = C_WARNING[wl]
        font_wl = QFont("Segoe UI", 11, QFont.Weight.Bold)
        p.setFont(font_wl)
        p.setPen(QPen(wl_color))
        wl_text = f"L{self._warning_level}" if not self._in_break else "☀️"
        p.drawText(w - 42, y, wl_text)

        # ─ Work / Timepass bar ──────────────────────────────────────────────────────────
        y += 16
        bar_x, bar_w_full, bar_h = 14, w - 28, 6
        total = (self._work_min + self._timepass_min) or 1
        work_pct = self._work_min / total
        # Background track
        track = QPainterPath()
        track.addRoundedRect(bar_x, y, bar_w_full, bar_h, 3, 3)
        p.fillPath(track, QBrush(QColor(255, 255, 255, 20)))
        # Work fill
        if work_pct > 0:
            work_fill = QPainterPath()
            work_fill.addRoundedRect(bar_x, y, max(6, bar_w_full * work_pct), bar_h, 3, 3)
            p.fillPath(work_fill, QBrush(C_WORK))

        # Timer labels
        y += bar_h + 12
        font_timer = QFont("Segoe UI", 8)
        p.setFont(font_timer)
        p.setPen(QPen(C_WORK))
        p.drawText(bar_x, y, f"✔ {self._work_min}m work")
        p.setPen(QPen(C_TIMEPASS))
        tp_text = f"■ {self._timepass_min}m timepass"
        fm2 = QFontMetrics(font_timer)
        p.drawText(w - fm2.horizontalAdvance(tp_text) - 14, y, tp_text)

        # ─ Separator ────────────────────────────────────────────────────────────────────────
        y += 14
        p.setPen(QPen(C_BORDER))
        p.drawLine(14, y, w - 14, y)

        # ─ Last Amma line ────────────────────────────────────────────────────────────────────
        y += 14
        font_line = QFont("Segoe UI", 8)
        font_line.setItalic(True)
        p.setFont(font_line)
        p.setPen(QPen(C_MUTED))
        # Word-wrap last_line to 2 lines max
        max_chars = 48
        text = self._last_line
        if len(text) > max_chars:
            # Try to break at a space
            break_at = text.rfind(" ", 0, max_chars)
            if break_at == -1:
                break_at = max_chars
            line1 = text[:break_at]
            line2 = text[break_at:].strip()[:max_chars]
        else:
            line1, line2 = text, ""
        p.drawText(16, y, line1)
        if line2:
            y += 14
            p.drawText(16, y, line2)

        p.end()

    # ── Drag support ─────────────────────────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, _event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, _event):
        """Double-click to toggle compact/expanded mode."""
        if self.height() == WIDGET_H:
            self.setFixedSize(WIDGET_W, 36)   # Compact — just the accent bar + title
        else:
            self.setFixedSize(WIDGET_W, WIDGET_H)


# ── AmmaOverlay — the public API called by main.py ────────────────────────────────
class AmmaOverlay:
    """Thread-safe wrapper. main.py calls overlay.update() from the asyncio
    background thread; Qt event loop runs in the main OS thread."""

    def __init__(self):
        self._queue: queue.Queue = queue.Queue(maxsize=50)
        self._widget: Optional[GlassWidget] = None
        self._app:    Optional[QApplication] = None
        self._timer:  Optional[QTimer] = None

    def start(self):
        """Init Qt widget — MUST be called from the main OS thread."""
        import sys
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._widget = GlassWidget()
        self._widget.show()
        self._widget.raise_()
        self._widget.activateWindow()
        # Poll the update queue every 100ms from the main thread
        self._timer = QTimer()
        self._timer.timeout.connect(self._drain_queue)
        self._timer.start(100)

    def run_event_loop(self):
        """Block the main thread running the Qt event loop. Returns on quit()."""
        if self._app:
            self._app.exec()

    def _drain_queue(self):
        while not self._queue.empty():
            try:
                state = self._queue.get_nowait()
                if self._widget:
                    self._widget.apply_state(state)
            except queue.Empty:
                break

    def update(
        self,
        classification: Optional[str] = None,
        warning_level:  Optional[int] = None,
        timepass_min:   Optional[int] = None,
        work_min:       Optional[int] = None,
        in_break:       Optional[bool] = None,
        last_line:      Optional[str] = None,
        mode:           Optional[str] = None,
    ):
        """Thread-safe state update from asyncio loop."""
        state = {}
        if classification is not None: state["classification"] = classification
        if warning_level  is not None: state["warning_level"]  = warning_level
        if timepass_min   is not None: state["timepass_min"]   = timepass_min
        if work_min       is not None: state["work_min"]       = work_min
        if in_break       is not None: state["in_break"]       = in_break
        if last_line      is not None: state["last_line"]      = last_line
        if mode           is not None: state["mode"]           = mode
        if state:
            try:
                self._queue.put_nowait(state)
            except queue.Full:
                pass  # Drop if queue full (non-critical UI)

    def stop(self):
        """Shut down the Qt overlay (safe to call from any thread)."""
        if self._timer:
            self._timer.stop()
        if self._app:
            self._app.quit()
