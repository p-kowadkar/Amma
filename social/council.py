"""
Global Amma Council — Ch 58-60
Weekly verdict generation, Hall of Pride/Shame, cultural pack verdicts.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
import random

# ── Verdict pools (Ch 58-59) ────────────────────────────────────────────────

PRIDE_VERDICTS = {
    "english": [
        "The Council nods approvingly. Do not let it go to your head. Next week, do it again.",
        "We are not easily impressed. This week, we are... not unimpressed. Continue.",
        "Your Amma has been telling us about you. We can see why. Keep going.",
        "Top 10%. The Council sees you. We are cautiously, carefully proud.",
        "This is what we like to see. Now do it three weeks in a row. Then we will talk.",
    ],
    "hindi": [
        "Sharma ji ka beta bhi itna nahi karta. Shabash.",
        "Council khush hai. Agle hafte bhi repeat karo.",
    ],
    "kannada": [
        "Council nodi, olledu anta helthide. Continue maadu.",
        "Nimma Amma helthidru. Naavu nambthivi.",
    ],
}

SHAME_VERDICTS = {
    "english": [
        "The Council expected better. We will try again next week.",
        "Disappointing does not quite cover it. The word has not been invented yet.",
        "Your mother has been informed. She agrees with our assessment.",
        "We tried to warn you on Wednesday. And Thursday. And Friday. Here we are.",
        "The Council has no further comment at this time. The score says enough.",
    ],
    "hindi": [
        "Sharma ji ka beta toh itna nahi girta tha... aur woh toh doctor ban gaya.",
        "Beta teri amma ko pata hai? Hamne bataya. Woh jaanti hai. Sab jaante hain.",
    ],
    "kannada": [
        "Yenu maadtidiya, heltiya? Ee vaara naachu bekaagthu.",
        "Nimma amma ge gottide. Ellarigu gottide. Seriously, ellarigu.",
    ],
}

NEUTRAL_VERDICTS = {
    "english": [
        "Middle of the pack. Not terrible. Not notable. Improve.",
        "The Council acknowledges your existence this week.",
    ],
    "hindi": ["Theek hai. Better kar sakte ho."],
    "kannada": ["Sari ide. Innashtu better maadu."],
}


@dataclass
class CouncilVerdict:
    user_id: str
    percentile: float       # 0-100
    score: int              # 0-100
    verdict_text: str
    hall_status: str         # pride | shame | neutral
    week_start: datetime
    cultural_pack: str = "english"


class AmmaCouncil:
    """Weekly council — runs Sunday 00:00 UTC (Ch 60.1)."""

    def generate_verdict(
        self,
        percentile: float,
        cultural_pack: str,
        score_data: dict,
    ) -> str:
        pack = cultural_pack if cultural_pack in PRIDE_VERDICTS else "english"
        if percentile >= 90:
            pool = PRIDE_VERDICTS[pack]
        elif percentile >= 60:
            pool = NEUTRAL_VERDICTS[pack]
        elif percentile >= 10:
            pool = NEUTRAL_VERDICTS[pack]
        else:
            pool = SHAME_VERDICTS[pack]

        base = random.choice(pool)

        if score_data.get("nuclear_events", 0) > 0:
            base += " The nuclear events did not go unnoticed."
        return base

    def compute_percentile(self, score: int, all_scores: List[int]) -> float:
        if not all_scores:
            return 50.0
        below = sum(1 for s in all_scores if s < score)
        return (below / len(all_scores)) * 100

    def run_weekly(self, user_scores: dict) -> List[CouncilVerdict]:
        """Process all user scores and generate verdicts."""
        all_scores = list(user_scores.values())
        verdicts = []
        for user_id, score_data in user_scores.items():
            score = score_data.get("score", 0)
            pct = self.compute_percentile(score, [s.get("score", 0) for s in user_scores.values()])
            hall = "pride" if pct >= 90 else ("shame" if pct <= 10 else "neutral")
            pack = score_data.get("cultural_pack", "english")
            text = self.generate_verdict(pct, pack, score_data)
            verdicts.append(CouncilVerdict(
                user_id=user_id, percentile=pct, score=score,
                verdict_text=text, hall_status=hall,
                week_start=datetime.now(timezone.utc), cultural_pack=pack,
            ))
        return verdicts
