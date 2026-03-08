"""
Wake Word System — Ch 28
Porcupine integration for offline "Hey Amma" detection.
Graceful fallback when Porcupine is not installed.
"""
import asyncio
from typing import AsyncGenerator, Callable, Optional, List

DEFAULT_WAKE_WORDS = ["hey amma", "amma"]


class WakeWordListener:
    """
    Listens for wake words using Picovoice Porcupine (offline).
    Falls back to disabled state if pvporcupine is not installed.
    """

    def __init__(
        self,
        access_key: str = "",
        wake_words: Optional[List[str]] = None,
        custom_keyword_paths: Optional[List[str]] = None,
        sensitivity: float = 0.7,
        on_wake: Optional[Callable[[str], None]] = None,
    ):
        self.access_key = access_key
        self.wake_words = wake_words or DEFAULT_WAKE_WORDS
        self.custom_keyword_paths = custom_keyword_paths or []
        self.sensitivity = sensitivity
        self.on_wake = on_wake
        self._running = False
        self._porcupine = None
        self._stream = None
        self._available = False
        self._labels: List[str] = []

    async def start(self):
        """Initialize Porcupine and begin listening. No-op if unavailable."""
        try:
            import pvporcupine
            import pyaudio
            import struct

            all_paths = self.custom_keyword_paths

            if all_paths:
                # Custom .ppn files only — pvporcupine doesn't mix built-in + custom
                self._porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keyword_paths=all_paths,
                    sensitivities=[self.sensitivity] * len(all_paths),
                )
                labels = [p.split("/")[-1].replace(".ppn", "") for p in all_paths]
            else:
                # Built-in keywords
                self._porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keywords=self.wake_words,
                    sensitivities=[self.sensitivity] * len(self.wake_words),
                )
                labels = self.wake_words

            pa = pyaudio.PyAudio()
            self._stream = pa.open(
                rate=self._porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self._porcupine.frame_length,
            )
            self._available = True
            self._running = True
            self._labels = labels
            print(f"[WakeWord] Porcupine initialized: {labels}")
            await self._listen_loop(struct)
        except ImportError:
            print("[WakeWord] pvporcupine not installed — wake word disabled.")
            self._available = False
        except Exception as e:
            print(f"[WakeWord] Init failed: {e} — wake word disabled.")
            self._available = False

    async def _listen_loop(self, struct_mod):
        """Continuously process audio frames for wake word detection."""
        while self._running and self._porcupine and self._stream:
            try:
                pcm = self._stream.read(self._porcupine.frame_length, exception_on_overflow=False)
                pcm_unpacked = struct_mod.unpack_from(
                    "h" * self._porcupine.frame_length, pcm
                )
                keyword_index = self._porcupine.process(pcm_unpacked)
                if keyword_index >= 0:
                    word = self._labels[keyword_index] if keyword_index < len(self._labels) else "hi-amma"
                    print(f"[WakeWord] Detected: '{word}'")
                    if self.on_wake:
                        self.on_wake(word)
            except Exception:
                pass
            await asyncio.sleep(0)  # Yield to event loop

    def stop(self):
        """Stop listening and clean up."""
        self._running = False
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
        if self._porcupine:
            try:
                self._porcupine.delete()
            except Exception:
                pass
        self._stream = None
        self._porcupine = None

    @property
    def is_available(self) -> bool:
        return self._available
