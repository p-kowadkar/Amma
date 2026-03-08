"""
Amma Vision Classifier — Gemini 3 Flash Preview
Classifies screen captures as WORK / GREY / TIMEPASS with NUCLEAR detection.
"""
import json
import base64
from dataclasses import dataclass
from typing import Optional

from google import genai
from google.genai import types

CLASSIFICATION_MODEL = "gemini-3-flash-preview"

CLASSIFICATION_PROMPT = """You are Amma's vision classifier. Analyze the screenshot and window title.

CLASSIFICATION RULES:
- WORK: Writing code, debugging, technical docs, Stack Overflow, GitHub, professional email, technical YouTube tutorials (code visible), terminal/IDE usage
- GREY: YouTube with ambiguous content, games, social media that could be professional, Reddit (depends on subreddit), browser with unclear page
- TIMEPASS: Netflix/streaming, dating apps, meme sites, casual gaming, doom scrolling, shopping (non-work), social media browsing

NUCLEAR DETECTION:
- Set nuclear to true ONLY if the content is clearly NSFW, pornographic, or extremely inappropriate
- This is a separate flag from classification — nuclear content is always TIMEPASS

IMPORTANT: Return GREY when confidence < 0.70. Do not guess.

Window title: {window_title}
Process: {process_name}

Respond ONLY with valid JSON (no markdown, no code fences):
{{
  "classification": "WORK|GREY|TIMEPASS",
  "confidence": 0.0,
  "reason": "one sentence",
  "nuclear": false,
  "dominant_app": "app or website name"
}}"""


@dataclass
class ClassificationResult:
    classification: str
    confidence: float
    reason: str
    nuclear: bool
    dominant_app: str


CONFIDENCE_THRESHOLD = 0.70


def parse_classification(raw: str) -> ClassificationResult:
    clean = raw.strip().strip("```json").strip("```").strip()
    start = clean.find("{")
    end = clean.rfind("}") + 1
    if start >= 0 and end > start:
        clean = clean[start:end]
    data = json.loads(clean)
    classification = data.get("classification", "GREY")
    confidence = float(data.get("confidence", 0.5))
    # Enforce confidence threshold: if below 0.70, force GREY (Ch 10)
    # Exception: nuclear content is always TIMEPASS regardless of confidence
    nuclear = bool(data.get("nuclear", False))
    if confidence < CONFIDENCE_THRESHOLD and not nuclear:
        classification = "GREY"
    return ClassificationResult(
        classification=classification,
        confidence=confidence,
        reason=data.get("reason", ""),
        nuclear=nuclear,
        dominant_app=data.get("dominant_app", "Unknown"),
    )


class GeminiClassifier:
    def __init__(self, client: genai.Client):
        self.client = client

    async def classify(self, frame) -> ClassificationResult:
        """Classify a ScreenFrame using Gemini vision."""
        if frame.is_private:
            return ClassificationResult(
                "WORK", 1.0, "Private window - not monitored", False, "private"
            )
        try:
            prompt = CLASSIFICATION_PROMPT.format(
                window_title=frame.window_title,
                process_name=frame.window_process,
            )

            contents = []
            if frame.image_b64:
                img_bytes = base64.b64decode(frame.image_b64)
                contents.append(
                    types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
                )
            contents.append(prompt)

            response = await self.client.aio.models.generate_content(
                model=CLASSIFICATION_MODEL,
                contents=contents,
            )
            # Gemini 3 Flash has thinking — filter to text-only parts, skip thought_signature
            text = ""
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text and not getattr(part, "thought", False):
                    text += part.text
            return parse_classification(text or response.text)
        except Exception as e:
            print(f"[Classifier] Error: {e}")
            return ClassificationResult(
                "GREY", 0.5, f"Classification error: {e}", False, "Unknown"
            )
