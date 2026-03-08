"""
Receipt Card Generator — Ch 62
Pillow-based session summary card: stats, grade, Amma quote.
Shareable PNG for Twitter/WhatsApp/Instagram.
"""
import io
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

from PIL import Image, ImageDraw, ImageFont


CARD_WIDTH = 600
CARD_HEIGHT = 800
BG_COLOR = (18, 18, 24)          # Dark background
ACCENT_COLOR = (255, 136, 0)     # Amma orange
TEXT_COLOR = (240, 240, 240)
MUTED_COLOR = (160, 160, 170)
WORK_COLOR = (76, 175, 80)       # Green
TIMEPASS_COLOR = (244, 67, 54)   # Red
GRADE_COLORS = {
    "S": (255, 215, 0),   # Gold
    "A": (76, 175, 80),   # Green
    "B": (33, 150, 243),  # Blue
    "C": (255, 152, 0),   # Orange
    "D": (244, 67, 54),   # Red
    "F": (198, 40, 40),   # Dark red
}


@dataclass
class SessionStats:
    """Data needed to render a receipt card."""
    user_name: str
    date: str
    work_minutes: int
    timepass_minutes: int
    efficiency: int          # 0-100
    longest_streak_min: int
    peak_warning: int
    nuclear_count: int
    level: int
    title: str
    streak_days: int
    xp_earned: int
    amma_quote: str = ""


def _efficiency_grade(eff: int) -> str:
    if eff >= 90: return "S"
    if eff >= 80: return "A"
    if eff >= 70: return "B"
    if eff >= 55: return "C"
    if eff >= 40: return "D"
    return "F"


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Try to load a system font, fall back to default."""
    font_names = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for name in font_names:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def generate_receipt_card(stats: SessionStats) -> bytes:
    """Generate a PNG receipt card and return as bytes."""
    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Fonts
    font_title = _get_font(28, bold=True)
    font_large = _get_font(48, bold=True)
    font_normal = _get_font(18)
    font_small = _get_font(14)
    font_stat = _get_font(22, bold=True)
    font_quote = _get_font(16)

    y = 30

    # ── Header ────────────────────────────────────────────
    draw.text((30, y), "Amma अम्मा", fill=ACCENT_COLOR, font=font_title)
    y += 40
    draw.text((30, y), "SESSION RECEIPT", fill=MUTED_COLOR, font=font_small)
    y += 25
    draw.line([(30, y), (CARD_WIDTH - 30, y)], fill=ACCENT_COLOR, width=2)
    y += 20

    # ── User & Date ───────────────────────────────────────
    draw.text((30, y), stats.user_name, fill=TEXT_COLOR, font=font_stat)
    draw.text((CARD_WIDTH - 180, y), stats.date, fill=MUTED_COLOR, font=font_normal)
    y += 40

    # ── Grade (big) ───────────────────────────────────────
    grade = _efficiency_grade(stats.efficiency)
    grade_color = GRADE_COLORS.get(grade, TEXT_COLOR)
    draw.text((CARD_WIDTH // 2 - 25, y), grade, fill=grade_color, font=_get_font(72, bold=True))
    y += 85
    draw.text((CARD_WIDTH // 2 - 60, y), f"{stats.efficiency}% EFFICIENCY",
              fill=MUTED_COLOR, font=font_normal)
    y += 40
    draw.line([(30, y), (CARD_WIDTH - 30, y)], fill=(50, 50, 60), width=1)
    y += 20

    # ── Work vs Timepass bar ──────────────────────────────
    total = stats.work_minutes + stats.timepass_minutes or 1
    work_pct = stats.work_minutes / total
    bar_x, bar_w, bar_h = 30, CARD_WIDTH - 60, 24
    # Work portion
    work_w = int(bar_w * work_pct)
    draw.rectangle([bar_x, y, bar_x + work_w, y + bar_h], fill=WORK_COLOR)
    # Timepass portion
    draw.rectangle([bar_x + work_w, y, bar_x + bar_w, y + bar_h], fill=TIMEPASS_COLOR)
    y += bar_h + 8
    draw.text((30, y), f"Work: {stats.work_minutes}m", fill=WORK_COLOR, font=font_small)
    draw.text((CARD_WIDTH - 160, y), f"Timepass: {stats.timepass_minutes}m",
              fill=TIMEPASS_COLOR, font=font_small)
    y += 35

    # ── Stats grid ────────────────────────────────────────
    stat_items = [
        ("Focus Streak", f"{stats.longest_streak_min}m"),
        ("Peak Warning", f"L{stats.peak_warning}"),
        ("Nuclear Events", str(stats.nuclear_count)),
        ("Streak", f"{stats.streak_days}d"),
        ("Level", f"{stats.level} — {stats.title}"),
        ("XP Earned", f"+{stats.xp_earned}"),
    ]
    col_w = (CARD_WIDTH - 60) // 2
    for i, (label, value) in enumerate(stat_items):
        col = i % 2
        row = i // 2
        x = 30 + col * col_w
        sy = y + row * 50
        draw.text((x, sy), label, fill=MUTED_COLOR, font=font_small)
        draw.text((x, sy + 18), value, fill=TEXT_COLOR, font=font_stat)
    y += (len(stat_items) // 2 + 1) * 50

    # ── Amma quote ────────────────────────────────────────
    if stats.amma_quote:
        draw.line([(30, y), (CARD_WIDTH - 30, y)], fill=(50, 50, 60), width=1)
        y += 15
        # Word wrap
        words = stats.amma_quote.split()
        lines = []
        current_line = ""
        for word in words:
            test = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test, font=font_quote)
            if bbox[2] > CARD_WIDTH - 80:
                lines.append(current_line)
                current_line = word
            else:
                current_line = test
        if current_line:
            lines.append(current_line)

        draw.text((40, y), '"', fill=ACCENT_COLOR, font=_get_font(28))
        y += 5
        for line in lines[:4]:  # Max 4 lines
            draw.text((50, y), line, fill=MUTED_COLOR, font=font_quote)
            y += 22

    # ── Footer ────────────────────────────────────────────
    y = CARD_HEIGHT - 40
    draw.text((30, y), "amma.dev", fill=MUTED_COLOR, font=font_small)
    draw.text((CARD_WIDTH - 150, y), "#AmmaIsWatching", fill=ACCENT_COLOR, font=font_small)

    # Export to PNG bytes
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def save_receipt_card(stats: SessionStats, path: str = "receipt.png"):
    """Generate and save receipt card to file."""
    png_bytes = generate_receipt_card(stats)
    with open(path, "wb") as f:
        f.write(png_bytes)
    print(f"[Receipt] Card saved to {path}")
    return path
