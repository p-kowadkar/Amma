"""Tests for AmmaVoice — PCM-to-WAV conversion and system prompt building."""
import io
import struct
import wave
import pytest
from unittest.mock import MagicMock
from voice import AmmaVoice
from config import AmmaConfig


class TestPcmToWav:
    def test_produces_valid_wav(self):
        """Generate some PCM data, convert, and verify WAV structure."""
        # 1 second of silence at 24kHz, 16-bit mono
        pcm = b"\x00\x00" * 24000
        wav_bytes = AmmaVoice._pcm_to_wav(pcm, sample_rate=24000)
        # Should start with RIFF header
        assert wav_bytes[:4] == b"RIFF"
        assert wav_bytes[8:12] == b"WAVE"

    def test_wav_params_correct(self):
        pcm = b"\x00\x00" * 24000  # 1 sec
        wav_bytes = AmmaVoice._pcm_to_wav(pcm, sample_rate=24000)
        buf = io.BytesIO(wav_bytes)
        with wave.open(buf, "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 24000
            assert wf.getnframes() == 24000

    def test_custom_sample_rate(self):
        pcm = b"\x00\x00" * 16000
        wav_bytes = AmmaVoice._pcm_to_wav(pcm, sample_rate=16000)
        buf = io.BytesIO(wav_bytes)
        with wave.open(buf, "rb") as wf:
            assert wf.getframerate() == 16000

    def test_empty_pcm(self):
        wav_bytes = AmmaVoice._pcm_to_wav(b"", sample_rate=24000)
        buf = io.BytesIO(wav_bytes)
        with wave.open(buf, "rb") as wf:
            assert wf.getnframes() == 0

    def test_round_trip_preserves_data(self):
        # Generate known pattern
        samples = [struct.pack("<h", i % 32767) for i in range(100)]
        pcm = b"".join(samples)
        wav_bytes = AmmaVoice._pcm_to_wav(pcm, sample_rate=24000)
        buf = io.BytesIO(wav_bytes)
        with wave.open(buf, "rb") as wf:
            recovered = wf.readframes(wf.getnframes())
        assert recovered == pcm


class TestBuildSystemPrompt:
    def _make_voice(self, config=None):
        mock_client = MagicMock()
        return AmmaVoice(client=mock_client, config=config)

    def test_without_config_returns_default(self):
        voice = self._make_voice(config=None)
        prompt = voice.build_system_prompt()
        assert "Amma" in prompt
        assert "South Indian" in prompt

    def test_with_config_includes_user_name(self):
        cfg = AmmaConfig(user_formal_name="Pranav", nickname="beta",
                         full_name="Pranav Kowadkar")
        voice = self._make_voice(config=cfg)
        prompt = voice.build_system_prompt()
        assert "Pranav" in prompt
        assert "beta" in prompt
        assert "Pranav Kowadkar" in prompt

    def test_includes_language_config(self):
        cfg = AmmaConfig(languages=["Kannada", "Hindi", "English"],
                         scold_language="Kannada", support_language="Hindi")
        voice = self._make_voice(config=cfg)
        prompt = voice.build_system_prompt()
        assert "Kannada" in prompt
        assert "Hindi" in prompt

    def test_includes_strictness_and_warmth(self):
        cfg = AmmaConfig(strictness=8, warmth=9)
        voice = self._make_voice(config=cfg)
        prompt = voice.build_system_prompt()
        assert "8" in prompt  # strictness
        assert "9" in prompt  # warmth

    def test_includes_cultural_pack(self):
        cfg = AmmaConfig(cultural_pack="south-indian-kannada")
        voice = self._make_voice(config=cfg)
        prompt = voice.build_system_prompt()
        assert "south-indian-kannada" in prompt

    def test_includes_inviolable_rules(self):
        cfg = AmmaConfig()
        voice = self._make_voice(config=cfg)
        prompt = voice.build_system_prompt()
        assert "Never apologize" in prompt
        assert "Never break character" in prompt


class TestVoiceInit:
    def test_voice_name_stored(self):
        mock_client = MagicMock()
        voice = AmmaVoice(client=mock_client, voice_name="Kore")
        assert voice.voice_name == "Kore"

    def test_default_voice_is_aoede(self):
        mock_client = MagicMock()
        voice = AmmaVoice(client=mock_client)
        assert voice.voice_name == "Aoede"

    def test_initial_state(self):
        mock_client = MagicMock()
        voice = AmmaVoice(client=mock_client)
        assert voice._session is None
        assert voice._use_fallback is False
