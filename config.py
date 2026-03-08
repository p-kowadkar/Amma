from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class AmmaConfig:
    # Identity
    user_formal_name: str = "Pranav"
    nickname: str = "beta"
    full_name: str = "Pranav Kowadkar"
    endearment: str = "beta"
    custom_terms: List[str] = field(default_factory=lambda: ["maga"])
    # Language
    languages: List[str] = field(default_factory=lambda: ["Kannada", "Hindi", "English"])
    scold_language: str = "Kannada"
    support_language: str = "Hindi"
    technical_language: str = "English"
    cultural_pack: str = "south-indian-kannada"
    # Personality
    strictness: int = 8
    warmth: int = 9
    guilt_trips: int = 8
    patience_minutes: int = 45
    humor: int = 6
    archetype: str = "classic"  # classic/modern/anxious/competitive/philosopher/dadi
    # Voice & audio
    voice_name: str = "Aoede"
    support_voice_name: str = "Kore"  # Voice for Support Mode (Ch 27)
    # API & system
    gemini_api_key: str = ""
    demo_mode: bool = False
    monitor_index: int = 0
    debounce_seconds: int = 30
    session_cap_hours: int = 12
    # Time-of-day
    timezone: str = "Asia/Kolkata"
    # Wake word
    picovoice_access_key: str = ""
    wake_words: List[str] = field(default_factory=lambda: ["hey amma", "amma"])
    custom_keyword_paths: List[str] = field(default_factory=list)
    # Customization
    custom_phrases: Dict[str, str] = field(default_factory=dict)
    # Daily session goals (set each launch, not persisted in config)
    goals: List[str] = field(default_factory=list)
    session_hours: Optional[float] = None
