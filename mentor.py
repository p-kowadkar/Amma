"""
Mentor Mode — Ch 84-95
Stuck detection, rubber duck protocol, skill gap tracker, on-demand teaching,
career guidance, and life phase adaptation.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
from collections import Counter, defaultdict


# ═══════════════════════════════════════════════════════════════════════════════
# MENTOR MODE CONFIG (Ch 84.3)
# ═══════════════════════════════════════════════════════════════════════════════

MENTOR_MODE_VOICE_CONFIG = {
    "voice": "Aoede",
    "volume": 0.65,
    "speaking_rate": 0.90,
    "temperature": 0.7,
}

MENTOR_MODE_SYSTEM_PROMPT = """\
You are now in Mentor Mode. The user has asked for help or is stuck.
Switch to teacher mode: patient, clear, structured.
Use the Socratic method where possible — ask questions before giving answers.
Reference the user's specific work context (current project, tech stack).
After the explanation, give one concrete exercise or next step.
Then return to your normal personality.
Never be condescending. You are teaching because you care, not because you are superior.
"""

TEACHING_TRIGGERS = [
    "amma explain", "amma teach me", "amma what is",
    "amma how does", "amma why does", "amma difference between",
    "amma i dont understand", "amma help me understand",
    "can you explain", "what is a", "how do i",
]


def is_teaching_request(text: str) -> bool:
    text_lower = text.lower().strip()
    return any(t in text_lower for t in TEACHING_TRIGGERS)


# ═══════════════════════════════════════════════════════════════════════════════
# STUCK DETECTION (Ch 85)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StuckDetector:
    """Detects when user is spinning in place — lots of deletes, repeated searches."""

    edit_history: List[dict] = field(default_factory=list)
    search_history: List[str] = field(default_factory=list)
    tab_switch_count: int = 0
    last_stuck_intervention: Optional[datetime] = None
    _cooldown_minutes: int = 30

    def record_edit(self, chars_added: int, chars_deleted: int):
        self.edit_history.append({
            "added": chars_added,
            "deleted": chars_deleted,
            "ts": datetime.now(timezone.utc),
        })
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
        self.edit_history = [e for e in self.edit_history if e["ts"] > cutoff]

    def record_search(self, query: str):
        self.search_history.append(query.lower().strip())
        self.search_history = self.search_history[-20:]

    def record_tab_switch(self):
        self.tab_switch_count += 1

    def reset_tab_switches(self):
        self.tab_switch_count = 0

    def is_stuck(self) -> bool:
        if len(self.edit_history) < 10:
            return False

        # Cooldown check
        if self.last_stuck_intervention:
            elapsed = (datetime.now(timezone.utc) - self.last_stuck_intervention).total_seconds()
            if elapsed < self._cooldown_minutes * 60:
                return False

        # Signal 1: net negative chars (more deletes than adds)
        net_chars = sum(e["added"] - e["deleted"] for e in self.edit_history)
        net_negative = net_chars < -50

        # Signal 2: repeated searches (same query 3+ times)
        search_counts = Counter(self.search_history[-20:])
        repeated_search = any(c >= 3 for c in search_counts.values())

        # Signal 3: high tab-switch rate
        high_tab_switch = self.tab_switch_count > 10

        # Stuck = at least 2 of 3 signals
        signals = [net_negative, repeated_search, high_tab_switch]
        return sum(signals) >= 2


STUCK_DIALOGUE = [
    "Beta, you have been at this for a while and I can see it is not moving. "
    "What is the problem? Talk me through it.",
    "I am watching the cursor. It keeps going back to the same place. "
    "What is catching you?",
    "You have searched for that three times in the last hour. "
    "Let me just explain it properly. What specifically is confusing?",
    "Beta, stop for one moment. What is the ONE thing blocking you right now? "
    "Say it out loud. To me.",
]

RUBBER_DUCK_PROMPT = (
    "Beta, stop. Do not look at the code for a moment. "
    "Tell me — in plain language, not code — "
    "what you are trying to make happen. "
    "Just describe it. I am listening."
)


# ═══════════════════════════════════════════════════════════════════════════════
# SKILL GAP TRACKER (Ch 87)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SkillGap:
    term: str
    count: int
    first_seen: datetime
    last_seen: datetime
    addressed: bool = False


class SkillGapTracker:
    """Tracks repeated searches to identify knowledge gaps (Ch 87.2)."""

    def __init__(self):
        self.search_counts: Dict[str, int] = defaultdict(int)
        self.search_history: Dict[str, List[datetime]] = defaultdict(list)
        self.addressed: set = set()

    def record_search(self, query: str):
        normalized = self._normalize(query)
        self.search_counts[normalized] += 1
        self.search_history[normalized].append(datetime.now(timezone.utc))

    def get_skill_gaps(self, min_count: int = 4) -> List[SkillGap]:
        gaps = []
        for term, count in self.search_counts.items():
            if count >= min_count and term not in self.addressed:
                gaps.append(SkillGap(
                    term=term,
                    count=count,
                    first_seen=self.search_history[term][0],
                    last_seen=self.search_history[term][-1],
                ))
        return sorted(gaps, key=lambda g: g.count, reverse=True)

    def mark_addressed(self, term: str):
        self.addressed.add(self._normalize(term))

    def _normalize(self, query: str) -> str:
        return query.lower().strip().replace(" ", "-")[:50]


# ═══════════════════════════════════════════════════════════════════════════════
# "I LOOKED IT UP" — PROACTIVE WEB EXPLANATION (Ch 88)
# ═══════════════════════════════════════════════════════════════════════════════

async def get_lookup_explanation(term: str, serper_client) -> Optional[str]:
    """Fetch a plain-English explanation for a repeatedly searched term.
    Uses Serper to find results, then summarises the key snippet."""
    if not serper_client or not serper_client.is_available:
        return None
    try:
        # Search for "what is {term}" + "how does {term} work"
        query = f"what is {term} how does it work simple explanation"
        results = await serper_client.search(query, num_results=3)
        if not results:
            return None
        snippets = []
        for item in results.get("organic", [])[:3]:
            snippet = item.get("snippet", "")
            if snippet and len(snippet) > 30:
                snippets.append(snippet[:250])
        if not snippets:
            return None
        # Return the first strong snippet as the explanation
        return snippets[0]
    except Exception as e:
        print(f"[Mentor] Lookup error for '{term}': {e}")
        return None


SKILL_GAP_DIALOGUE = [
    "Beta. You have searched for {term} {count} times this week. "
    "{count} separate times. We are fixing this right now.",
    "You have looked up {term} {count} times in the last month. "
    "This ends today. I am teaching you this properly.",
    "I have noticed you keep searching {term}. "
    "This is a quick explanation. Can I give it to you?",
]


# ═══════════════════════════════════════════════════════════════════════════════
# LIFE PHASE ADAPTATION (Ch 95)
# ═══════════════════════════════════════════════════════════════════════════════

LIFE_PHASES = {
    "STUDENT": {
        "focus": "study hours, assignments, exam prep",
        "tone": "more patient, more teaching",
    },
    "JOB_HUNTING": {
        "focus": "applications/day, interview prep, networking",
        "tone": "urgently supportive, career-aware",
    },
    "EARLY_CAREER": {
        "focus": "skill building, output quality, visibility",
        "tone": "ambitious, forward-focused",
    },
    "MID_CAREER": {
        "focus": "impact, leadership, strategic thinking",
        "tone": "peer-level respect, less hand-holding",
    },
    "SENIOR": {
        "focus": "legacy, mentorship, strategic moves",
        "tone": "deeply respected, highly autonomous",
    },
}


def detect_life_phase(
    in_school: bool = False,
    years_experience: int = 0,
    employment_status: str = "employed",
) -> str:
    if in_school:
        return "STUDENT"
    if employment_status == "seeking" or years_experience == 0:
        return "JOB_HUNTING"
    if years_experience < 3:
        return "EARLY_CAREER"
    if years_experience < 8:
        return "MID_CAREER"
    return "SENIOR"


# ═══════════════════════════════════════════════════════════════════════════════
# TEACHING RESPONSE STRUCTURE (Ch 86.2)
# ═══════════════════════════════════════════════════════════════════════════════

TEACHING_SYSTEM_PROMPT = """\
The user has asked you to explain something. You are now in Teacher Mode.

STRUCTURE YOUR EXPLANATION AS:
1. Start with a single, concrete real-world analogy (not abstract)
2. Give the precise technical definition (one sentence)
3. Show the simplest possible working example
4. Explain ONE common mistake or misconception
5. Give one exercise the user can do RIGHT NOW to verify understanding
6. Ask one follow-up question to check comprehension

CALIBRATION:
- Reference their current project/tech stack if relevant
- Never repeat what they already clearly know
- If the concept is simple: be brief. Do not pad.

VOICE DELIVERY:
- Explanations are spoken, not read. Use natural pauses.
- Shorter sentences than written text.
- End with: 'Does that make sense? What part should I go deeper on?'
"""
