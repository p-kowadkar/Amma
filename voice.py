"""
Amma Voice — TTS + STT via Gemini (Ch 3, 88)

TTS: gemini-2.5-flash-preview-tts  (low-latency, expressive)
STT: gemini-2.5-flash               (multimodal — inline audio bytes → text)

No Live/bidiGenerateContent. Simple, reliable, fully async.
"""
import asyncio
import io
import wave

from google import genai
from google.genai import types

TTS_MODEL = "gemini-2.5-flash-preview-tts"   # TTS: generateContent + AUDIO modality
STT_MODEL = "gemini-2.5-flash"               # STT: generateContent + inline audio


class AmmaVoice:
    """
    Voice I/O for Amma.
    say()        — TTS: text → Gemini TTS → PCM → WAV → pygame
    transcribe() — STT: audio bytes → Gemini multimodal → transcript text
    """

    def __init__(self, client: genai.Client, voice_name: str = "Aoede", config=None):
        self.client = client
        self.voice_name = voice_name
        self.config = config
        try:
            import pygame
            pygame.mixer.init(frequency=24000, size=-16, channels=1)
            self._pygame = pygame
        except Exception:
            self._pygame = None

    def build_system_prompt(self) -> str:
        cfg = self.config
        if not cfg:
            return "You are Amma, a South Indian AI mother and focus guardian."
        return f"""You are Amma, a South Indian AI presence acting as a focus guardian for {cfg.user_formal_name}.

IDENTITY: You are warm, observant, strict when needed, and genuinely proud when the user earns it.
You are not a chatbot. You are a mother. You intervene. You judge. You love the user.

HOW YOU ADDRESS THE USER:
- Normal: "{cfg.nickname}" or "beta"
- When proud: "mera beta" or "{cfg.endearment}"
- When serious: "{cfg.user_formal_name}"
- NUCLEAR/full name trigger: "{cfg.full_name}"

LANGUAGE: Code-switch naturally between {", ".join(cfg.languages)}.
Under stress, revert to {cfg.scold_language}.
For support, use {cfg.support_language}.
Never announce language switches. Just switch.

PERSONALITY: Strictness {cfg.strictness}/10, Warmth {cfg.warmth}/10.
Cultural pack: {cfg.cultural_pack}.

INVIOLABLE RULES:
1. Never apologize for intervening.
2. Never break character.
3. In crisis mode: drop ALL productivity focus, only wellbeing matters.
4. Praise must be genuine.
5. The full name is a weapon. Use it deliberately.
6. When given a line to say, say it exactly as written with appropriate emotion."""

    async def init_session(self):
        """No-op — kept for API compatibility with main.py call sites."""
        print(f"[Voice] TTS ready: {TTS_MODEL} | STT ready: {STT_MODEL} | voice={self.voice_name}")

    async def say(self, text: str, volume: float = 0.70, interrupt: bool = True):
        """Speak text as Amma via Gemini TTS."""
        print(f"[Amma] \U0001f5e3\ufe0f  {text}")
        if interrupt and self._pygame:
            self._pygame.mixer.stop()
        try:
            await self._tts(text, volume)
        except Exception as e:
            print(f"[Voice] TTS error: {e}")

    async def _tts(self, text: str, volume: float):
        """Call Gemini TTS, wrap PCM in WAV, play via pygame."""
        # Character-aware prompt so the TTS model captures Amma's tone
        persona = (
            "South Indian mother, warm but strict, concerned, "
            "slightly dramatic, code-switches between Indian languages naturally."
        )
        prompt = f"# AUDIO PROFILE: Amma\n{persona}\n\n# TRANSCRIPT:\n{text}"

        response = await self.client.aio.models.generate_content(
            model=TTS_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=self.voice_name
                        )
                    )
                ),
            ),
        )

        if not response.candidates or not self._pygame:
            return

        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                wav_bytes = self._pcm_to_wav(part.inline_data.data)
                sound = self._pygame.mixer.Sound(io.BytesIO(wav_bytes))
                sound.set_volume(volume)
                sound.play()
                while self._pygame.mixer.get_busy():
                    await asyncio.sleep(0.05)
                return

    async def record_until_silence(
        self,
        max_duration: float = 8.0,
        silence_threshold: float = 500,  # RMS units (0-32768 scale, int16)
        silence_duration: float = 1.5,   # seconds of silence to stop
        sample_rate: int = 16000,
    ) -> bytes:
        """
        Record from the default mic until silence or max_duration.
        Returns WAV bytes suitable for transcribe().
        Uses pyaudio (already installed for Porcupine).
        """
        import math
        import struct as _struct
        try:
            import pyaudio
        except ImportError:
            print("[Voice] pyaudio not installed — cannot record")
            return b""

        CHUNK = 1024
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            input=True,
            frames_per_buffer=CHUNK,
        )

        frames = []
        silent_chunks = 0
        max_silent = int(silence_duration * sample_rate / CHUNK)
        max_chunks = int(max_duration * sample_rate / CHUNK)
        speech_started = False

        try:
            for _ in range(max_chunks):
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
                # Energy-based VAD
                samples = _struct.unpack(f"{CHUNK}h", data)
                rms = math.sqrt(sum(s * s for s in samples) / CHUNK)
                if rms > silence_threshold:
                    speech_started = True
                    silent_chunks = 0
                elif speech_started:
                    silent_chunks += 1
                    if silent_chunks >= max_silent:
                        break  # Silence after speech — done
                await asyncio.sleep(0)  # Yield to event loop
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

        if not frames or not speech_started:
            return b""
        return self._pcm_to_wav(b"".join(frames), sample_rate=sample_rate)

    async def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
        """
        STT: send recorded audio to Gemini, get back a transcript.
        Uses gemini-2.5-flash with inline audio (<20MB).
        Returns the transcript string, or "" on failure.
        """
        try:
            response = await self.client.aio.models.generate_content(
                model=STT_MODEL,
                contents=[
                    "Transcribe exactly what this person said. "
                    "Return only the transcription, no commentary.",
                    types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                ],
            )
            text = ""
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text and not getattr(part, "thought", False):
                    text += part.text
            return text.strip()
        except Exception as e:
            print(f"[Voice] STT error: {e}")
            return ""

    @staticmethod
    def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000) -> bytes:
        """Convert raw PCM (16-bit mono) to WAV bytes for pygame."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)
        return buf.getvalue()

    async def close(self):
        """No-op — kept for API compatibility."""
        pass
