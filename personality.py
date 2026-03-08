"""
Personality Engine — Vol III/IV (Ch 23-25, 31)
Archetypes, setup interview flow, personality calibration.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ── Archetypes (Ch 31.4) ────────────────────────────────────────────────────
@dataclass
class Archetype:
    name: str
    description: str
    strictness: int
    warmth: int
    guilt_trips: int
    patience_minutes: int
    humor: int


ARCHETYPES: Dict[str, Archetype] = {
    "classic": Archetype(
        name="The Classic",
        description="Maximum guilt, zero chill, deeply invested.",
        strictness=9, warmth=8, guilt_trips=10, patience_minutes=40, humor=4,
    ),
    "modern": Archetype(
        name="The Modern Amma",
        description="Updated references, occasional meme awareness, still screams.",
        strictness=7, warmth=8, guilt_trips=7, patience_minutes=45, humor=7,
    ),
    "anxious": Archetype(
        name="The Anxious Amma",
        description="Every notification is a potential crisis. Extremely attentive.",
        strictness=8, warmth=9, guilt_trips=8, patience_minutes=35, humor=3,
    ),
    "competitive": Archetype(
        name="The Competitive Amma",
        description="Everything compared to someone. Relentless motivation.",
        strictness=9, warmth=6, guilt_trips=9, patience_minutes=30, humor=5,
    ),
    "philosopher": Archetype(
        name="The Philosopher Amma",
        description="Quotes before scolding. Long pauses. Devastating observations.",
        strictness=7, warmth=7, guilt_trips=6, patience_minutes=50, humor=6,
    ),
    "dadi": Archetype(
        name="The Dadi Amma",
        description="Grandmother energy. Slower to anger, deeper disappointment.",
        strictness=5, warmth=10, guilt_trips=7, patience_minutes=60, humor=5,
    ),
}


def apply_archetype(config, archetype_key: str):
    """Apply archetype personality parameters to an AmmaConfig."""
    arch = ARCHETYPES.get(archetype_key)
    if not arch:
        return
    config.strictness = arch.strictness
    config.warmth = arch.warmth
    config.guilt_trips = arch.guilt_trips
    config.patience_minutes = arch.patience_minutes
    config.humor = arch.humor


# ── Setup Interview (Ch 31.1) ───────────────────────────────────────────────
SETUP_QUESTIONS = [
    ("formal_name", "What is your name? The one I should use when I am being serious."),
    ("nickname", "And what do your people call you at home? Your nickname."),
    ("full_name", "And your full name — the one your mother uses when she means business."),
    ("languages", "What languages do we speak at home? List them all."),
    ("scold_language", "When I am very frustrated with you, which language should I use?"),
    ("support_language", "And when you need comfort — which language feels like home?"),
    ("archetype", "What kind of Amma do you need? classic / modern / anxious / competitive / philosopher / dadi"),
    ("custom_phrase", "Is there something your actual mother says that I should know? Any specific phrase she uses that hits different?"),
]


@dataclass
class SetupInterview:
    """Manages the first-launch setup conversation."""
    questions: List[tuple] = field(default_factory=lambda: list(SETUP_QUESTIONS))
    answers: Dict[str, str] = field(default_factory=dict)
    current_index: int = 0
    completed: bool = False

    @property
    def current_question(self) -> Optional[tuple]:
        if self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None

    def answer(self, response: str) -> Optional[tuple]:
        """Record answer and return next question, or None if done."""
        if self.current_index < len(self.questions):
            key, _ = self.questions[self.current_index]
            self.answers[key] = response
            self.current_index += 1
        if self.current_index >= len(self.questions):
            self.completed = True
            return None
        return self.questions[self.current_index]

    def apply_to_config(self, config):
        """Apply interview answers to AmmaConfig."""
        if "formal_name" in self.answers:
            config.user_formal_name = self.answers["formal_name"]
        if "nickname" in self.answers:
            config.nickname = self.answers["nickname"]
        if "full_name" in self.answers:
            config.full_name = self.answers["full_name"]
        if "languages" in self.answers:
            config.languages = [l.strip() for l in self.answers["languages"].split(",")]
        if "scold_language" in self.answers:
            config.scold_language = self.answers["scold_language"]
        if "support_language" in self.answers:
            config.support_language = self.answers["support_language"]
        if "archetype" in self.answers:
            apply_archetype(config, self.answers["archetype"].strip().lower())
        if "custom_phrase" in self.answers and self.answers["custom_phrase"].strip():
            config.custom_phrases["general"] = self.answers["custom_phrase"]


# ── Language Profile (Ch 29) ────────────────────────────────────────────────
CODE_SWITCH_EXAMPLES = {
    "gentle": [
        "Beta, kya kar rahe ho? This is not what we discussed.",
        "Yenu maadtidiya, I thought you were working.",
    ],
    "firm": [
        "Band mado idu. Right now. Sari?",
        "Ittu saaku. Close it now. Please.",
    ],
    "scream": [
        "YENU MAADTIDIYA?! KELTIYA NAANU?! CLOSE IT NOW!!",
        "BAND KARO WO ABHI!! EK SECOND MEIN!! ABHI!!",
    ],
    "pride": [
        "Beta... *sighs happily* ...mera beta. I am so proud.",
        "Nanna maga. This is exactly what I knew you could do.",
    ],
}


def get_code_switch_prompt(languages: List[str], scold_lang: str, support_lang: str) -> str:
    """Generate the code-switching instruction block for the system prompt."""
    return f"""Code-switch naturally as a real multilingual person would.
Primary languages: {', '.join(languages)}.
Under stress, revert to {scold_lang}.
For comfort and pride, use {support_lang}.
Never announce language switches. Just switch."""
