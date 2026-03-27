"""
Amma Local Database — Phase 3
SQLite-backed persistence for session history, weekly scores, and council verdicts.
Stored at ~/.amma/amma.db — never uploaded, never shared.
"""
import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

AMMA_DB_PATH = Path.home() / ".amma" / "amma.db"


def _connect() -> sqlite3.Connection:
    AMMA_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(AMMA_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                date         TEXT    NOT NULL,
                work_min     INTEGER DEFAULT 0,
                timepass_min INTEGER DEFAULT 0,
                efficiency   INTEGER DEFAULT 0,
                peak_warning INTEGER DEFAULT 0,
                nuclear_count INTEGER DEFAULT 0,
                trust_label  TEXT    DEFAULT 'MEDIUM',
                xp_earned    INTEGER DEFAULT 0,
                goals        TEXT    DEFAULT '[]',
                created_at   TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS weekly_scores (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start  TEXT NOT NULL UNIQUE,
                score       INTEGER DEFAULT 0,
                grade       TEXT    DEFAULT 'C',
                hall_status TEXT    DEFAULT 'neutral',
                verdict     TEXT    DEFAULT '',
                created_at  TEXT    NOT NULL
            )
        """)
        conn.commit()


class AmmoDB:
    """Local SQLite store for session history and weekly scores."""

    def __init__(self):
        init_db()

    # ── Session persistence ─────────────────────────────────────────────────

    def save_session(self, date_str: str, work_min: int, timepass_min: int,
                     efficiency: int, peak_warning: int, nuclear_count: int,
                     trust_label: str, xp_earned: int, goals: list):
        with _connect() as conn:
            conn.execute(
                """INSERT INTO sessions
                       (date, work_min, timepass_min, efficiency, peak_warning,
                        nuclear_count, trust_label, xp_earned, goals, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (date_str, work_min, timepass_min, efficiency, peak_warning,
                 nuclear_count, trust_label, xp_earned,
                 json.dumps(goals), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()

    def get_recent_sessions(self, days: int = 7) -> List[dict]:
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        with _connect() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE date >= ? ORDER BY date DESC",
                (cutoff,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_week_sessions(self, week_start: date) -> List[dict]:
        week_end = (week_start + timedelta(days=6)).isoformat()
        with _connect() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE date BETWEEN ? AND ? ORDER BY date",
                (week_start.isoformat(), week_end),
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Weekly scoring ──────────────────────────────────────────────────────

    def save_weekly_score(self, week_start: str, score: int, grade: str,
                          hall_status: str, verdict: str):
        with _connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO weekly_scores
                       (week_start, score, grade, hall_status, verdict, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (week_start, score, grade, hall_status, verdict,
                 datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()

    def get_all_weekly_scores(self) -> List[dict]:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT * FROM weekly_scores ORDER BY week_start DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Trend analysis ──────────────────────────────────────────────────────

    def get_weekly_trend(self) -> str:
        """Compare this week vs last week average efficiency → improving/declining/stable."""
        recent = self.get_recent_sessions(14)
        if len(recent) < 2:
            return "stable"
        today = date.today()
        this_week_start = today - timedelta(days=today.weekday())
        this_week = [s for s in recent if s["date"] >= this_week_start.isoformat()]
        last_week = [s for s in recent if s["date"] < this_week_start.isoformat()]
        if not this_week or not last_week:
            return "stable"
        avg_this = sum(s["efficiency"] for s in this_week) / len(this_week)
        avg_last = sum(s["efficiency"] for s in last_week) / len(last_week)
        if avg_this > avg_last + 5:
            return "improving"
        if avg_this < avg_last - 5:
            return "declining"
        return "stable"

    def get_week_avg_efficiency(self, week_start: date) -> Optional[float]:
        sessions = self.get_week_sessions(week_start)
        if not sessions:
            return None
        return sum(s["efficiency"] for s in sessions) / len(sessions)

    # ── WeeklyReportCard inputs ─────────────────────────────────────────────

    def compute_weekly_report_card_inputs(self, week_start: date) -> dict:
        """Aggregate session data for WeeklyReportCard computation."""
        sessions = self.get_week_sessions(week_start)
        if not sessions:
            return {}
        total_work = sum(s["work_min"] for s in sessions)
        total_time = sum(s["work_min"] + s["timepass_min"] for s in sessions) or 1
        nuclear_total = sum(s["nuclear_count"] for s in sessions)
        reset_days = sum(1 for s in sessions if s["efficiency"] >= 80)
        return {
            "focus_time_pct": total_work / total_time,
            "consistency_score": min(len(sessions) / 7.0, 1.0),
            "nuclear_events": nuclear_total,
            "late_night_3am_count": 0,  # Would need sleep data
            "reset_days": reset_days,
            "session_count": len(sessions),
        }
