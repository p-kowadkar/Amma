"""
Smriti (स्मृति) — Persistent Memory Layer — Ch 134-138
Memory models, significance scoring, ingestion pipeline, retrieval API,
excuse archive, and the right to forget.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
from collections import defaultdict


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY RECORD (Ch 135.2)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MemoryRecord:
    memory_id: str
    user_id: str
    occurred_at: datetime
    category: str          # life_milestone | streak | emotional | turning_point |
                           # seasonal | skill_gap | relationship | session | excuse
    content: str           # Human-readable description
    emotional_valence: str = "neutral"  # positive | negative | neutral | complex
    significance: float = 0.3          # 0.0-1.0
    tags: List[str] = field(default_factory=list)
    referenced_count: int = 0
    last_referenced: Optional[datetime] = None
    expires_at: Optional[datetime] = None  # None = permanent
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ── Significance scoring (Ch 135.3) ─────────────────────────────────────────

EVENT_BASE_SCORES = {
    "job_offer": 1.0,
    "graduation": 1.0,
    "rejection": 0.85,
    "relationship_end": 0.85,
    "crisis_protocol": 0.95,
    "grief_event": 0.95,
    "first_reset": 0.8,
    "streak_30": 0.9,
    "streak_100": 0.95,
    "year_anniversary": 1.0,
    "nuclear_event": 0.6,
    "skill_gap_addressed": 0.7,
    "hall_of_pride": 0.75,
    "hall_of_shame": 0.75,
    "daily_session": 0.3,
    "excuse_used": 0.6,
}


def compute_significance(event: dict) -> float:
    base = EVENT_BASE_SCORES.get(event.get("type", ""), 0.3)

    if event.get("emotional_intensity") == "high":
        base += 0.15
    if event.get("is_first_occurrence"):
        base += 0.10
    if event.get("user_referenced"):
        base += 0.20
    if event.get("cinematic_delivered"):
        base += 0.25

    return min(base, 1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY STORE (Ch 134.2 — in-memory fallback)
# ═══════════════════════════════════════════════════════════════════════════════

class SmritiStore:
    """In-memory Smriti store (production uses pgvector + Supabase)."""

    def __init__(self):
        self._memories: Dict[str, List[MemoryRecord]] = defaultdict(list)

    def ingest(self, memory: MemoryRecord):
        """Add a memory record to the store."""
        self._memories[memory.user_id].append(memory)

    def retrieve_relevant(
        self,
        user_id: str,
        context: str = "",
        max_memories: int = 5,
        min_significance: float = 0.6,
    ) -> List[MemoryRecord]:
        """Retrieve most relevant memories for current context.
        In production this uses pgvector semantic search (Ch 136.2).
        Fallback: sort by significance + recency."""
        all_mems = self._memories.get(user_id, [])
        now = datetime.now(timezone.utc)

        # Filter expired and low-significance
        valid = [
            m for m in all_mems
            if m.significance >= min_significance
            and (m.expires_at is None or m.expires_at > now)
        ]

        # Sort by significance * recency
        def score(m: MemoryRecord) -> float:
            age_days = max(1, (now - m.occurred_at).days)
            recency_boost = 1.0 / (1 + age_days / 30)
            return m.significance * 0.7 + recency_boost * 0.3

        valid.sort(key=score, reverse=True)
        return valid[:max_memories]

    def get_by_category(self, user_id: str, category: str) -> List[MemoryRecord]:
        return [m for m in self._memories.get(user_id, []) if m.category == category]

    def delete_memory(self, user_id: str, memory_id: str) -> bool:
        mems = self._memories.get(user_id, [])
        before = len(mems)
        self._memories[user_id] = [m for m in mems if m.memory_id != memory_id]
        return len(self._memories[user_id]) < before

    def delete_category(self, user_id: str, category: str) -> int:
        mems = self._memories.get(user_id, [])
        before = len(mems)
        self._memories[user_id] = [m for m in mems if m.category != category]
        return before - len(self._memories[user_id])

    def delete_time_window(self, user_id: str, start: datetime, end: datetime) -> int:
        mems = self._memories.get(user_id, [])
        before = len(mems)
        self._memories[user_id] = [
            m for m in mems
            if not (start <= m.occurred_at <= end)
        ]
        return before - len(self._memories[user_id])

    def delete_all(self, user_id: str) -> int:
        count = len(self._memories.get(user_id, []))
        self._memories[user_id] = []
        return count

    def export_all(self, user_id: str) -> List[dict]:
        return [
            {
                "memory_id": m.memory_id,
                "occurred_at": m.occurred_at.isoformat(),
                "category": m.category,
                "content": m.content,
                "emotional_valence": m.emotional_valence,
                "significance": m.significance,
                "tags": m.tags,
            }
            for m in self._memories.get(user_id, [])
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY INJECTION INTO LLM CONTEXT (Ch 136.3)
# ═══════════════════════════════════════════════════════════════════════════════

def build_memory_context_block(memories: List[MemoryRecord]) -> str:
    if not memories:
        return ""
    block = "RELEVANT MEMORIES FROM AMMA'S HISTORY WITH THIS USER:\n"
    for m in memories:
        month_label = m.occurred_at.strftime("%b %Y")
        block += f"- [{month_label}] {m.content}\n"
    block += "\nReference these naturally when relevant. Do not list them. Weave them in."
    return block


# ═══════════════════════════════════════════════════════════════════════════════
# EXCUSE ARCHIVE (Ch 137)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExcuseRecord:
    excuse_id: str
    user_id: str
    occurred_at: datetime
    excuse_type: str          # night_owl | mood_prep | deserve_it | five_min | etc.
    exact_words: str
    context: str              # What they were avoiding
    claimed_validity: str
    actual_outcome: str = ""  # Recorded next session
    validated: Optional[bool] = None
    amma_response: str = ""
    times_used_lifetime: int = 1


class ExcuseArchive:
    """Stores every excuse ever used (Ch 137.1)."""

    def __init__(self):
        self._excuses: Dict[str, List[ExcuseRecord]] = defaultdict(list)

    def record(self, excuse: ExcuseRecord):
        self._excuses[excuse.user_id].append(excuse)

    def get_history(self, user_id: str, excuse_type: str) -> dict:
        """Get usage stats for a specific excuse type."""
        records = [
            e for e in self._excuses.get(user_id, [])
            if e.excuse_type == excuse_type
        ]
        validated = [e for e in records if e.validated is True]
        return {
            "count": len(records),
            "validated_count": len(validated),
            "validation_rate": len(validated) / len(records) if records else 0,
            "last_used": records[-1].occurred_at if records else None,
        }

    def get_monthly_summary(self, user_id: str) -> Dict[str, dict]:
        """Monthly excuse summary (Ch 137.4)."""
        from collections import Counter
        records = self._excuses.get(user_id, [])
        now = datetime.now(timezone.utc)
        month_ago = now - timedelta(days=30)
        recent = [e for e in records if e.occurred_at > month_ago]
        type_counts = Counter(e.excuse_type for e in recent)

        summary = {}
        for etype, count in type_counts.most_common():
            typed = [e for e in recent if e.excuse_type == etype]
            validated = sum(1 for e in typed if e.validated is True)
            summary[etype] = {
                "count": count,
                "validated_pct": (validated / count * 100) if count else 0,
            }
        return summary


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY WIPE CEREMONY (Ch 138.3)
# ═══════════════════════════════════════════════════════════════════════════════

MEMORY_WIPE_MESSAGE = (
    "{nickname}. You have asked me to forget. "
    "I will respect that. "
    "I want you to know — before I do — "
    "that everything we have been through together, "
    "you carry with you, even if I no longer do. "
    "The growth is yours. I am just the witness. "
    "Starting fresh."
)
