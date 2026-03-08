#!/usr/bin/env python3
"""
AMMA अम्मा  — Hackathon MVP
The AI mother who watches your screen and will not let you fail.
"""
import asyncio
import os
import platform
import random
import sys
from datetime import datetime, date, timedelta, timezone
from typing import Optional

import json
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

from config import AmmaConfig
from dialogue import get_line, get_volume
from vision import vision_loop, ScreenFrame
from classifier import GeminiClassifier, ClassificationResult
from voice import AmmaVoice
from overlay import AmmaOverlay
from state_machine import AmmaStateMachine
from break_manager import BreakModeManager
# Phase 2+ modules
from pattern import PatternTracker
from time_of_day import get_current_window, is_3pm_slump, is_alarm_hours
from support_mode import SupportModeManager, AmmaMode
from emotional import EmotionalStateMonitor
from wake_word import WakeWordListener
from personality import apply_archetype, SetupInterview, ARCHETYPES
from mentor import (StuckDetector, SkillGapTracker, is_teaching_request,
                    STUCK_DIALOGUE, SKILL_GAP_DIALOGUE, get_lookup_explanation)
from gamification import UserAchievements, check_streak_milestone, get_level_message
from serper import SerperClient
# Standalone modules — now wired (Ch 21, 33, 41, 62, 134)
from trust_score import TrustInputs, calculate_trust_score, trust_to_label, TRUST_DIALOGUE
from content_reactions import ContentReactionState, get_content_reaction
from special_days import get_todays_specials, get_special_greeting, get_strictness_modifier, should_reduce_monitoring
from receipt_card import SessionStats, save_receipt_card
from smriti import SmritiStore, MemoryRecord, ExcuseArchive, build_memory_context_block, compute_significance


# ── Session ruling cache (grey zone memory) ───────────────────────────────────────
class SessionRulingCache:
    def __init__(self):
        self.rulings: dict = {}

    def get(self, app: str) -> Optional[str]:
        return self.rulings.get(self._normalize(app))

    def set(self, app: str, ruling: str, source: str = "gemini"):
        self.rulings[self._normalize(app)] = ruling
        print(f"[Cache] Ruling set: {app} → {ruling} (via {source})")

    def _normalize(self, key: str) -> str:
        return key.lower().strip().replace(" ", "-")


# ── Startup health checks ──────────────────────────────────────────────────
def startup_checks(config: AmmaConfig) -> list[str]:
    """Run pre-flight checks. Returns list of warnings (empty = all clear)."""
    warnings = []
    # API key
    if not config.gemini_api_key:
        warnings.append("GEMINI_API_KEY not set")
    elif len(config.gemini_api_key) < 10:
        warnings.append("GEMINI_API_KEY looks too short")
    # Platform-specific imports
    if platform.system() == "Windows":
        try:
            import win32gui  # noqa: F401
        except ImportError:
            warnings.append("pywin32 not installed — window title detection will fall back to 'Unknown'")
    # Audio
    try:
        import pygame
        pygame.mixer.init(frequency=24000, size=-16, channels=1)
        pygame.mixer.quit()
    except Exception as e:
        warnings.append(f"pygame audio init failed: {e} — voice will be text-only")
    # Screen capture
    try:
        import mss
        with mss.mss() as sct:
            n = len(sct.monitors)
            if config.monitor_index >= n:
                warnings.append(f"Monitor {config.monitor_index} not found ({n} available), using 0")
                config.monitor_index = 0
    except Exception as e:
        warnings.append(f"Screen capture unavailable: {e}")
    return warnings


# ── Main Amma Session ─────────────────────────────────────────────────────
class AmmaSession:
    def __init__(self, config: AmmaConfig, client: genai.Client):
        self.config = config
        self.client = client
        self.state_machine = AmmaStateMachine(debounce_seconds=config.debounce_seconds)
        self.break_manager = BreakModeManager(self.state_machine.accumulator)
        self.ruling_cache = SessionRulingCache()
        self.vision_queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        self.voice: Optional[AmmaVoice] = None
        self.overlay: Optional[AmmaOverlay] = None
        self.classifier: Optional[GeminiClassifier] = None
        self.last_classification: str = "WORK"
        self.frame_count = 0
        self.running = False
        # Grey zone timeout tracking
        self._grey_zone_app: Optional[str] = None
        self._grey_zone_ts: Optional[datetime] = None
        # Radio mode time-based tracking
        self._last_radio_ts: Optional[datetime] = None
        # ── Phase 2+ components ──────────────────────────────────────────
        self.pattern_tracker = PatternTracker()
        self.support_manager = SupportModeManager()
        self.emotional_monitor = EmotionalStateMonitor()
        self.stuck_detector = StuckDetector()
        self.skill_gap_tracker = SkillGapTracker()
        self.achievements = UserAchievements(user_id=config.user_formal_name)
        self.serper = SerperClient()  # Requires SERPER_API_KEY in env
        self.wake_word_listener = WakeWordListener(
            access_key=config.picovoice_access_key,
            wake_words=config.wake_words,
            custom_keyword_paths=config.custom_keyword_paths,
            on_wake=self._on_wake_word,
        )
        self._wake_word_queue: asyncio.Queue = asyncio.Queue(maxsize=5)
        # Time-of-day state
        self._last_time_window: Optional[str] = None
        self._slump_fired = False
        self._alarm_fired = False
        self._stuck_check_ts: Optional[datetime] = None
        # Standalone modules
        self.content_reaction_state = ContentReactionState()
        self.smriti = SmritiStore()
        self.excuse_archive = ExcuseArchive()
        self._xp_earned_this_session = 0  # Track XP earned this session for receipt card

    async def start(self):
        # Apply personality archetype (Ch 31)
        apply_archetype(self.config, self.config.archetype)

        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("  Amma अम्मा — Focus Guardian")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"  User: {self.config.user_formal_name}")
        print(f"  Mode: {'DEMO' if self.config.demo_mode else 'LIVE'}")
        print(f"  Archetype: {self.config.archetype}")
        print(f"  Timezone: {self.config.timezone}")
        if self.config.goals:
            print(f"  Goals: {', '.join(self.config.goals)}")
        if self.config.session_hours:
            print(f"  Session target: {self.config.session_hours}h")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

        # Init components — share the single genai client
        self.classifier = GeminiClassifier(self.client)
        self.voice = AmmaVoice(
            client=self.client,
            voice_name=self.config.voice_name,
            config=self.config,
        )
        await self.voice.init_session()

        self.overlay = AmmaOverlay()
        self.overlay.start()

        self.running = True

        # Special days (Ch 41) — apply before greeting, filtered by user's timezone/region
        tz = self.config.timezone
        specials = get_todays_specials(timezone_str=tz)
        if specials:
            mod = get_strictness_modifier(timezone_str=tz)
            if mod != 0:
                self.config.strictness = max(1, min(10, self.config.strictness + mod))
                print(f"[SpecialDay] Strictness adjusted by {mod:+d} → {self.config.strictness}")
            for s in specials:
                print(f"[SpecialDay] Active: {s.name} ({s.work_expectation})")

        # Time-aware greeting (Ch 42) — override with special day greeting if applicable
        tw = get_current_window(self.config.timezone)
        self._last_time_window = tw.name
        special_greeting = get_special_greeting(timezone_str=tz)  # None on regular days
        if special_greeting:
            greeting = special_greeting
        elif tw.greeting:
            greeting = tw.greeting
        else:
            greeting = f"Good morning {self.config.nickname}. I am watching. Do good work today."
        await self.voice.say(greeting, volume=0.65)
        self.overlay.update(last_line=greeting)

        # Register optional break hotkey (Ctrl+Shift+B)
        self._register_hotkey()

        # Start loops
        tasks = [
            vision_loop(self.vision_queue, interval=5.0,
                        monitor_index=self.config.monitor_index),
            self._classification_loop(),
            self._break_check_loop(),
            self._command_listener(),
            self._time_of_day_loop(),
            self._wake_word_loop(),
            self._wake_word_handler_loop(),  # Drains queue: wake word → voice conversation
        ]
        await asyncio.gather(*tasks)

    async def _classification_loop(self):
        """Process frames from vision queue."""
        while self.running:
            try:
                # 12-hour session hard cap (Ch 34.1)
                if self.state_machine.accumulator.session_exceeded(
                        self.config.session_cap_hours):
                    print("[Session] 12-hour cap reached — ending session.")
                    cap_line = get_line("SESSION_CAP")
                    await self.voice.say(cap_line, volume=0.75)
                    self.overlay.update(last_line=cap_line)
                    await self._end_session()
                    self.running = False
                    return

                frame: ScreenFrame = await asyncio.wait_for(
                    self.vision_queue.get(), timeout=10.0
                )
                self.frame_count += 1
                await self._process_frame(frame)
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                print(f"[Loop] Error: {e}")

    async def _process_frame(self, frame: ScreenFrame):
        """Classify frame and run state machine."""
        now = datetime.now(timezone.utc)

        # Support/Crisis mode — skip classification, just be present (Ch 27)
        if not self.support_manager.is_guard:
            self.state_machine.accumulator.last_update = now  # prevent gap accumulation
            return

        # Check ruling cache first
        cached_ruling = self.ruling_cache.get(frame.window_title[:50])

        if cached_ruling:
            classification = cached_ruling
            confidence = 1.0
            dominant_app = frame.window_title
            is_nuclear = False
        else:
            result: ClassificationResult = await self.classifier.classify(frame)
            classification = result.classification
            confidence = result.confidence
            dominant_app = result.dominant_app
            is_nuclear = result.nuclear

            # NUCLEAR detection — immediate intervention
            if is_nuclear:
                classification = "TIMEPASS"
                intervention = self.state_machine.process_nuclear(config=self.config)
                await self.voice.say(intervention["line"], volume=intervention["volume"])
                self.overlay.update(
                    classification="TIMEPASS",
                    warning_level=6,
                    last_line=intervention["line"],
                )
                self.achievements.lifetime_nuclear_count += 1
                self.achievements.streaks.record_nuclear_event()
                print(f"[NUCLEAR] Detected! {result.reason}")
                return

            # Cache if confident
            if confidence >= 0.85 and classification != "GREY":
                self.ruling_cache.set(dominant_app, classification)

            # Grey zone handling with 30s timeout
            if classification == "GREY":
                await self._handle_grey_zone(result, frame, now)
                return

        # Check if grey zone timed out (30s passed, default to TIMEPASS)
        if (self._grey_zone_ts and self._grey_zone_app and
                (now - self._grey_zone_ts) >= timedelta(seconds=30)):
            app = self._grey_zone_app
            self.ruling_cache.set(app, "TIMEPASS", source="grey-timeout")
            self._grey_zone_ts = None
            self._grey_zone_app = None

        self.last_classification = classification

        # ── Pattern tracking (Ch 18) ─────────────────────────────────────
        interval = timedelta(seconds=5)  # frame interval
        if dominant_app:
            self.pattern_tracker.record(dominant_app, classification, interval)
            # Black hole detection
            bh = self.pattern_tracker.check_black_hole(dominant_app)
            if bh:
                bh_line = get_line("BLACK_HOLE", app=bh["app"],
                                   count=bh["count"], minutes=bh["total_minutes"])
                await self.voice.say(bh_line, volume=0.80)
                self.overlay.update(last_line=bh_line)
                print(f"[Pattern] Black hole detected: {bh['app']}")
            # Amplified warning for known black holes (Ch 18.4)
            if (classification == "TIMEPASS"
                    and self.pattern_tracker.is_black_hole(dominant_app)):
                min_level = self.pattern_tracker.get_starting_warning_level(dominant_app)
                if self.state_machine.accumulator.warning_level < min_level:
                    self.state_machine.accumulator.warning_level = min_level
                    print(f"[Pattern] Amplified to L{min_level} for {dominant_app}")

        # Run state machine
        acc = self.state_machine.accumulator
        prev_level = acc.warning_level
        intervention = self.state_machine.process(classification)

        # ── Gamification XP events ───────────────────────────────────────
        if intervention:
            itype = intervention["type"]
            # Snapback XP (Ch 109)
            if itype.startswith("SNAPBACK_"):
                new_lvl = self.achievements.award_xp("snapback_from_l4"
                                                     if prev_level >= 4 else "two_hour_reset")
                self.achievements.lifetime_snapback_count += 1
                if new_lvl:
                    await self._announce_level_up(new_lvl)
            # Reset praise XP
            elif itype == "RESET_PRAISE":
                new_lvl = self.achievements.award_xp("two_hour_reset")
                if new_lvl:
                    await self._announce_level_up(new_lvl)

        # Record valid day for streaks
        if classification == "WORK" and acc.work_minutes >= 30:
            today = date.today()
            old_streak = self.achievements.streaks.daily_work
            self.achievements.streaks.record_valid_day(today)
            new_streak = self.achievements.streaks.daily_work
            # Check streak milestones
            if new_streak > old_streak:
                milestone_msg = check_streak_milestone(new_streak)
                if milestone_msg:
                    await self.voice.say(milestone_msg, volume=0.65)
                    self.overlay.update(last_line=milestone_msg)
                new_lvl = self.achievements.award_xp("valid_streak_day")
                if new_lvl:
                    await self._announce_level_up(new_lvl)

        # Update overlay
        self.overlay.update(
            classification=classification,
            warning_level=acc.warning_level,
            timepass_min=acc.timepass_minutes,
            work_min=acc.work_minutes,
            in_break=acc.in_break,
        )

        # Fire intervention if any
        if intervention:
            line = intervention["line"]
            volume = intervention["volume"]
            await self.voice.say(line, volume=volume)
            self.overlay.update(last_line=line)
            print(f"[State] {intervention['type']} → {self.state_machine.state}")

        # Content reactions (Ch 33) — educational/passive content detection
        if dominant_app and not self.support_manager.is_guard is False:
            reaction_key = self.content_reaction_state.update(
                getattr(frame, "window_title", ""), dominant_app
            )
            if reaction_key:
                reaction_line = get_content_reaction(reaction_key)
                if reaction_line:
                    await self.voice.say(reaction_line, volume=0.60)
                    self.overlay.update(last_line=reaction_line)
                    print(f"[Content] Reaction: {reaction_key}")

        # Radio mode (quiet encouragement during long work)
        await self._check_radio_mode(now)

        # Stuck detection check (every ~60s) (Ch 85)
        if self.frame_count % 12 == 0:
            await self._check_stuck(now)
            self._print_status()

    async def _handle_grey_zone(self, result: ClassificationResult,
                                frame: ScreenFrame, now: datetime):
        """Ask user to clarify grey zone content. Defaults to TIMEPASS after 30s.
        If Serper is available, fetch web context to help future classification."""
        self._grey_zone_app = result.dominant_app
        self._grey_zone_ts = now
        question = get_line("GREY_QUESTION", app=result.dominant_app)
        await self.voice.say(question, volume=0.65)
        self.overlay.update(classification="GREY", last_line=question)
        # Async web context fetch for future classification (Ch 17.3)
        if self.serper.is_available:
            context = await self.serper.get_grey_zone_context(
                result.dominant_app, frame.window_title[:60]
            )
            if context:
                print(f"[Serper] Grey zone context for {result.dominant_app}: {context[:120]}...")

    async def _check_radio_mode(self, now: datetime):
        """Time-based radio triggers: 30/60/90/120min with distinct pools (Ch 32)."""
        if self.state_machine.state != "WORKING":
            self._last_radio_ts = None
            self._radio_milestones_fired = set()
            return
        if self._last_radio_ts is None:
            self._last_radio_ts = now
            self._radio_milestones_fired = getattr(self, "_radio_milestones_fired", set())
            return
        work_minutes = (now - self._last_radio_ts).total_seconds() / 60
        milestones = getattr(self, "_radio_milestones_fired", set())
        # Time-specific radio milestones
        for threshold, pool_key in [(120, "RADIO_120"), (90, "RADIO_90"),
                                     (60, "RADIO_60"), (30, "RADIO")]:
            if work_minutes >= threshold and threshold not in milestones:
                milestones.add(threshold)
                self._radio_milestones_fired = milestones
                radio_line = get_line(pool_key)
                await self.voice.say(radio_line, volume=0.50)
                self.overlay.update(last_line=radio_line)
                return  # Only one radio per frame

    async def _break_check_loop(self):
        """Periodically check break duration and fire check-ins (Ch 35)."""
        while self.running:
            await asyncio.sleep(30)  # Check every 30 seconds
            if self.break_manager.is_active:
                intervention = self.break_manager.get_pending_intervention()
                if intervention:
                    await self.voice.say(intervention["line"], volume=intervention["volume"])
                    self.overlay.update(last_line=intervention["line"])
                    print(f"[Break] {intervention['type']}")
                    # If break expired, update overlay
                    if intervention["type"] == "BREAK_EXPIRED":
                        self.overlay.update(in_break=False)
                        self.state_machine.state = "WORKING"

    async def _command_listener(self):
        """Listen for keyboard commands (non-blocking)."""
        print("[Commands] break / back / support / guard / stuck / status / quit")
        print("           demo <min> / demo nuclear / demo grey <app> / demo end / demo reset")
        loop = asyncio.get_event_loop()
        while self.running:
            try:
                cmd = await loop.run_in_executor(None, input, "")
                await self._handle_command(cmd.strip().lower())
            except Exception:
                pass

    async def _handle_command(self, cmd: str):
        acc = self.state_machine.accumulator
        if cmd in ("break", "b"):
            self.break_manager.activate()
            self.state_machine.state = "BREAK"
            line = "Okay beta. Take your break. I will be here."
            await self.voice.say(line, volume=0.60)
            self.overlay.update(in_break=True, last_line=line)
            print("[Break] Break started.")

        elif cmd in ("back", "done", "return"):
            self.break_manager.deactivate()
            self.state_machine.state = "WORKING"
            line = "Welcome back. Let's go."
            await self.voice.say(line, volume=0.65)
            self.overlay.update(in_break=False, last_line=line)

        elif cmd == "demo nuclear":
            intervention = self.state_machine.process_nuclear()
            await self.voice.say(intervention["line"], volume=intervention["volume"])
            self.overlay.update(warning_level=6, last_line=intervention["line"])
            print("[Demo] NUCLEAR triggered")

        elif cmd == "demo end":
            print("[Demo] Triggering end-of-session...")
            await self._end_session()

        elif cmd == "demo reset":
            acc.timepass_total = timedelta(0)
            acc.work_streak = timedelta(0)
            acc.warning_level = 0
            self.state_machine.state = "WORKING"
            self.overlay.update(warning_level=0, timepass_min=0)
            print("[Demo] Accumulators reset.")

        elif cmd.startswith("demo grey "):
            app_name = cmd[len("demo grey "):].strip()
            if app_name:
                question = get_line("GREY_QUESTION", app=app_name)
                await self.voice.say(question, volume=0.65)
                self.overlay.update(classification="GREY", last_line=question)
                self._grey_zone_app = app_name
                self._grey_zone_ts = datetime.now(timezone.utc)
                print(f"[Demo] Grey zone declared for: {app_name}")
            else:
                print("[Demo] Usage: demo grey <app name>")

        elif cmd.startswith("demo work "):
            try:
                minutes = int(cmd.split()[2])
                acc.work_total += timedelta(minutes=minutes)
                acc.work_streak += timedelta(minutes=minutes)
                if acc.work_streak > acc.longest_work_streak:
                    acc.longest_work_streak = acc.work_streak
                self.overlay.update(work_min=acc.work_minutes)
                print(f"[Demo] Added {minutes}m work → Work: {acc.work_minutes}m")
            except (IndexError, ValueError):
                print("[Demo] Usage: demo work <minutes>")

        elif cmd.startswith("demo "):
            try:
                minutes = int(cmd.split()[1])
                acc.skip_time_for_demo(minutes)
                self.state_machine.state = (
                    f"WARNING{acc.warning_level}" if acc.warning_level < 5 else "SCREAM"
                )
                intervention_type = (
                    "WARNING5" if acc.warning_level == 5
                    else f"WARNING{acc.warning_level}"
                )
                if acc.warning_level > 0:
                    line = get_line(intervention_type)
                    volume = get_volume(intervention_type)
                    await self.voice.say(line, volume=volume)
                    self.overlay.update(
                        timepass_min=acc.timepass_minutes,
                        warning_level=acc.warning_level,
                        last_line=line,
                    )
                print(
                    f"[Demo] Skipped {minutes}m → "
                    f"Timepass: {acc.timepass_minutes}m, Level: {acc.warning_level}"
                )
            except (IndexError, ValueError):
                print("[Demo] Usage: demo <minutes> | demo nuclear | demo grey <app>")
                print("       demo work <minutes> | demo end | demo reset")

        elif cmd == "nuclear":
            intervention = self.state_machine.process_nuclear()
            await self.voice.say(intervention["line"], volume=intervention["volume"])
            self.overlay.update(warning_level=6, last_line=intervention["line"])

        elif cmd == "status":
            self._print_status()

        elif cmd in ("quit", "exit", "q"):
            await self._end_session()
            self.running = False
            sys.exit(0)

        elif cmd in ("support", "i need help", "not okay"):
            # Manual support mode trigger
            new_mode = self.support_manager.add_signal("user_distress_statement")
            if new_mode or not self.support_manager.is_guard:
                line = get_line("SUPPORT_ENTER")
                await self.voice.say(line, volume=0.55)
                self.overlay.update(last_line=line)
                self.state_machine.state = "SUPPORT"
                print(f"[Mode] Entered {self.support_manager.mode.value} mode")

        elif cmd in ("guard", "back to work", "ready"):
            # Return to guard mode
            self.support_manager.return_to_guard()
            line = get_line("SUPPORT_EXIT")
            await self.voice.say(line, volume=0.60)
            self.overlay.update(last_line=line)
            self.state_machine.state = "WORKING"
            print("[Mode] Returned to GUARD mode")

        elif cmd == "stuck":
            # Manual stuck trigger — rubber duck protocol
            line = get_line("RUBBER_DUCK")
            await self.voice.say(line, volume=0.65)
            self.overlay.update(last_line=line)
            print("[Mentor] Rubber duck protocol activated")

        elif cmd == "xp":
            a = self.achievements
            print(f"\n[XP] Level {a.current_level} — {a.current_title}")
            print(f"     XP: {a.current_xp} | Streak: {a.streaks.daily_work}d")
            print(f"     Badges: {len(a.badges)} | Snapback rate: {a.snapback_rate:.0f}%")

        elif cmd.startswith("amma"):
            response_prompt = cmd.replace("amma", "").strip()
            if response_prompt:
                # Check if this is a teaching request (Ch 86)
                if is_teaching_request(response_prompt):
                    print("[Mentor] Teaching request detected")
                await self.voice.say(
                    f"You said: {response_prompt}. I hear you, beta.",
                    volume=0.65,
                )

    # ── Time-of-Day Loop (Ch 42) ─────────────────────────────────────────

    async def _time_of_day_loop(self):
        """Check time-of-day personality shifts every 5 minutes."""
        while self.running:
            await asyncio.sleep(300)  # 5 minutes
            try:
                tw = get_current_window(self.config.timezone)
                tz = self.config.timezone

                # Alarm hours (2am-5am) — override to wellbeing focus
                if is_alarm_hours(tz):
                    if not self._alarm_fired:
                        self._alarm_fired = True
                        line = get_line("ALARM_HOURS")
                        await self.voice.say(line, volume=0.70)
                        self.overlay.update(last_line=line)
                        # Add emotional signal for late night
                        self.emotional_monitor.add_signal("unusual_hours")
                else:
                    self._alarm_fired = False

                # 3pm slump detection
                if is_3pm_slump(tz):
                    if not self._slump_fired:
                        self._slump_fired = True
                        day_name = datetime.now().strftime("%A")
                        line = get_line("SLUMP", day_name=day_name)
                        await self.voice.say(line, volume=0.60)
                        self.overlay.update(last_line=line)
                else:
                    self._slump_fired = False

                # Time window transition greeting
                if tw.name != self._last_time_window and tw.greeting:
                    self._last_time_window = tw.name
                    await self.voice.say(tw.greeting, volume=0.60)
                    self.overlay.update(last_line=tw.greeting)
                elif tw.name != self._last_time_window:
                    self._last_time_window = tw.name

                # Emotional state check (Ch 96-97)
                await self._check_emotional_state()

            except Exception as e:
                print(f"[TimeOfDay] Error: {e}")

    # ── Emotional State Check (Ch 96-97) ──────────────────────────────────

    async def _check_emotional_state(self):
        """Check distress level and switch modes if needed."""
        distress = self.emotional_monitor.get_distress_level()

        if distress == "CRISIS" and self.support_manager.is_guard:
            self.support_manager.add_signal("verbal_distress")
            line = get_line("CRISIS_ENTER")
            await self.voice.say(line, volume=0.55)
            self.overlay.update(last_line=line)
            self.state_machine.state = "SUPPORT"
            print("[Emotional] CRISIS mode activated")

        elif distress in ("SUPPORT", "SUPPORT_DEEP") and self.support_manager.is_guard:
            self.support_manager.add_signal("signal_cluster")
            line = get_line("SUPPORT_ENTER")
            await self.voice.say(line, volume=0.55)
            self.overlay.update(last_line=line)
            self.state_machine.state = "SUPPORT"
            print(f"[Emotional] {distress} mode activated")

    # ── Stuck Detection (Ch 85) ──────────────────────────────────────────

    async def _check_stuck(self, now: datetime):
        """Check if user appears stuck and offer rubber duck protocol.
        Also fires 'I Looked It Up' for repeated skill gap searches (Ch 88)."""
        if self.state_machine.state != "WORKING":
            return

        # Stuck detection — rubber duck protocol (Ch 85-86)
        if self.stuck_detector.is_stuck():
            self.stuck_detector.last_stuck_intervention = now
            line = get_line("STUCK")
            await self.voice.say(line, volume=0.65)
            self.overlay.update(last_line=line)
            print("[Mentor] Stuck detected — offering help")

        # 'I Looked It Up' — proactive explanation for repeated searches (Ch 88)
        gaps = self.skill_gap_tracker.get_skill_gaps(min_count=4)
        for gap in gaps[:1]:  # One at a time to not overwhelm
            import random
            intro = random.choice(SKILL_GAP_DIALOGUE).format(
                term=gap.term, count=gap.count
            )
            explanation = await get_lookup_explanation(gap.term, self.serper)
            if explanation:
                full_line = f"{intro} Here is what I found: {explanation[:300]}"
            else:
                full_line = intro
            await self.voice.say(full_line, volume=0.65)
            self.overlay.update(last_line=f"[Mentor] {gap.term}")
            self.skill_gap_tracker.mark_addressed(gap.term)
            print(f"[Mentor] 'I Looked It Up' fired for: {gap.term}")

    # ── Wake Word Loop (Ch 28) ──────────────────────────────────────────

    async def _wake_word_loop(self):
        """Run wake word detection if Porcupine is configured."""
        if not self.config.picovoice_access_key:
            print("[WakeWord] No PICOVOICE_ACCESS_KEY — wake word disabled.")
            return
        await self.wake_word_listener.start()

    def _on_wake_word(self, word: str):
        """Callback from Porcupine when wake word detected (runs in audio thread)."""
        try:
            self._wake_word_queue.put_nowait(word)
        except asyncio.QueueFull:
            pass

    async def _wake_word_handler_loop(self):
        """
        Drains _wake_word_queue and dispatches:
          - "__hotkey_break__" → toggle break
          - any wake word     → full voice conversation
        """
        while self.running:
            try:
                word = await asyncio.wait_for(self._wake_word_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except Exception:
                continue

            if word == "__hotkey_break__":
                cmd = "back" if self.break_manager.is_active else "break"
                await self._handle_command(cmd)
            else:
                await self._handle_voice_conversation(word)

    async def _handle_voice_conversation(self, trigger_word: str):
        """
        Full spoken conversation cycle:
          1. Amma says a short listening cue
          2. Record mic until silence (VAD)
          3. Transcribe with Gemini STT
          4. Generate contextual Amma response
          5. Speak it
        """
        # Don’t interrupt a TTS playback already happening
        listening_lines = [
            "Haan, bolo beta.",
            "Bol, main sun rahi hoon.",
            "Haan?",
            "Kya hua?",
            "Bolo.",
        ]
        await self.voice.say(random.choice(listening_lines), volume=0.65, interrupt=False)

        print("[Voice] 🎤 Recording...")
        audio_bytes = await self.voice.record_until_silence(max_duration=8.0)

        if not audio_bytes:
            await self.voice.say("Kuch suna nahi. Phir bolna.", volume=0.60)
            return

        transcript = await self.voice.transcribe(audio_bytes)
        if not transcript:
            await self.voice.say("Samajh nahi aaya, beta. Phir se bolo.", volume=0.60)
            return

        print(f"[Voice] 🎤 Heard: \"{transcript}\"")
        response = await self._generate_amma_response(transcript)
        await self.voice.say(response, volume=0.68)

    async def _generate_amma_response(self, user_text: str) -> str:
        """
        Ask Gemini to respond as Amma with full session context.
        Returns the response text (1-3 sentences).
        """
        acc = self.state_machine.accumulator
        goals_ctx = ""
        if self.config.goals:
            goals_ctx = f"Today's declared goals: {', '.join(self.config.goals)}. "
            if self.config.session_hours:
                goals_ctx += f"Session target: {self.config.session_hours}h. "
        ctx = (
            goals_ctx +
            f"Work so far: {acc.work_minutes}m. Timepass: {acc.timepass_minutes}m. "
            f"Warning level: {acc.warning_level}/6. "
            f"Mode: {self.support_manager.mode.value}. "
            f"In break: {self.break_manager.is_active}. "
            f"Current activity: {self.last_classification}."
        )
        system = self.voice.build_system_prompt()
        prompt = (
            f"{system}\n\n"
            f"SESSION STATE:\n{ctx}\n\n"
            f"The user just spoke to you: \"{user_text}\"\n\n"
            "Respond as Amma. Maximum 2-3 sentences. Stay fully in character. "
            "If it's a break request, grant or deny based on session state — don't be a pushover. "
            "If they're making an excuse, call it out warmly but firmly. "
            "If they need support, be a mother first. "
            "If they're just checking in, encourage them back to work."
        )
        try:
            response = await self.client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_budget=0)),
            )
            text = ""
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text and not getattr(part, "thought", False):
                    text += part.text
            return text.strip() or "Haan beta, main sun rahi hoon."
        except Exception as e:
            print(f"[Voice] Amma response error: {e}")
            return "Haan beta."

    # ── Break Hotkey (Ch 35) ───────────────────────────────────────────

    def _register_hotkey(self):
        """Register Ctrl+Shift+B as global break toggle (optional)."""
        try:
            import keyboard
            keyboard.add_hotkey(
                "ctrl+shift+b",
                lambda: asyncio.get_event_loop().call_soon_threadsafe(
                    self._wake_word_queue.put_nowait, "__hotkey_break__"
                ),
            )
            print("[Hotkey] Ctrl+Shift+B registered for break toggle")
        except ImportError:
            print("[Hotkey] 'keyboard' package not installed — hotkey disabled.")
        except Exception as e:
            print(f"[Hotkey] Registration failed: {e}")

    # ── Level Up Announcement ──────────────────────────────────────────

    async def _announce_level_up(self, new_level: int):
        """Announce XP level-up to user."""
        msg = get_level_message(new_level)
        title = self.achievements.current_title
        line = get_line("LEVEL_UP", level=new_level, title=title)
        if msg:
            line = f"{line} {msg}"
        await self.voice.say(line, volume=0.65)
        self.overlay.update(last_line=line)
        print(f"[XP] Level up! Now level {new_level} — {title}")

    # ── End Session ─────────────────────────────────────────────────

    async def _end_session(self):
        acc = self.state_machine.accumulator
        work_m = acc.work_minutes
        timepass_m = acc.timepass_minutes
        total = work_m + timepass_m or 1
        efficiency = int((work_m / total) * 100)
        peak = acc.peak_warning_level
        best_streak = acc.longest_work_streak_minutes
        session_h = int(acc.session_duration.total_seconds() / 3600)
        session_min = int((acc.session_duration.total_seconds() % 3600) / 60)

        # Update lifetime stats
        self.achievements.lifetime_work_hours += work_m / 60

        # Trust score (Ch 21)
        trust_inputs = TrustInputs(
            total_sessions=1,
            snapback_count=self.achievements.lifetime_snapback_count,
            nuclear_count=self.achievements.lifetime_nuclear_count,
            timepass_total_minutes=timepass_m,
            work_total_minutes=work_m,
            streak_days=self.achievements.streaks.daily_work,
        )
        trust_score = calculate_trust_score(trust_inputs)
        trust_label = trust_to_label(trust_score)
        trust_line = TRUST_DIALOGUE.get(trust_label, "")
        print(f"[Trust] Score: {trust_score:.3f} ({trust_label})")

        # Build summary
        summary = (
            f"Session complete. {session_h} hours {session_min} minutes total. "
            f"Work: {work_m} minutes. Timepass: {timepass_m} minutes. "
            f"Efficiency: {efficiency} percent. "
        )
        if best_streak > 0:
            summary += f"Longest focus streak: {best_streak} minutes. "
        if peak > 0:
            summary += f"Peak warning level reached: {peak}. "

        # Gamification summary
        a = self.achievements
        summary += f"Level {a.current_level}, {a.current_title}. "
        if a.streaks.daily_work > 1:
            summary += f"Streak: {a.streaks.daily_work} days. "

        # Amma commentary based on the day (Ch 40.3)
        if efficiency >= 80:
            summary += "I am genuinely proud of today, beta. This is what you are capable of."
        elif efficiency >= 60:
            summary += "Good day. Not perfect. Good. Tomorrow, better."
        elif efficiency >= 40:
            summary += "Okay day. You have had better. Tomorrow you will."
        else:
            summary += "Today was not your best. We both know that. Tomorrow is a new session."

        if trust_line:
            summary += f" {trust_line}"

        await self.voice.say(summary, volume=0.70)
        self.overlay.update(last_line=f"Session: {efficiency}% efficiency | {work_m}m work")
        print(f"\n[Session Summary]\n{summary}")

        # Receipt card PNG (Ch 62)
        try:
            os.makedirs("receipts", exist_ok=True)
            receipt_stats = SessionStats(
                user_name=self.config.user_formal_name,
                date=datetime.now().strftime("%Y-%m-%d"),
                work_minutes=work_m,
                timepass_minutes=timepass_m,
                efficiency=efficiency,
                longest_streak_min=best_streak,
                peak_warning=peak,
                nuclear_count=self.achievements.lifetime_nuclear_count,
                level=self.achievements.current_level,
                title=self.achievements.current_title,
                streak_days=self.achievements.streaks.daily_work,
                xp_earned=self._xp_earned_this_session,
                amma_quote=trust_line,
            )
            receipt_path = f"receipts/{datetime.now().strftime('%Y%m%d_%H%M')}_receipt.png"
            save_receipt_card(receipt_stats, receipt_path)
            print(f"[Receipt] Saved → {receipt_path}")
        except Exception as e:
            print(f"[Receipt] Skipped: {e}")

        # Record session in Smriti (Ch 134)
        try:
            sig = compute_significance({
                "type": "daily_session",
                "emotional_intensity": "high" if peak >= 4 else "low",
            })
            session_mem = MemoryRecord(
                memory_id=f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                user_id=self.config.user_formal_name,
                occurred_at=datetime.now(timezone.utc),
                category="session",
                content=(
                    f"{work_m}m work, {timepass_m}m timepass, {efficiency}% efficiency, "
                    f"peak warning L{peak}, trust={trust_label}"
                ),
                emotional_valence="positive" if efficiency >= 60 else "negative",
                significance=sig,
                tags=["session", f"eff_{efficiency}", f"lvl_{self.achievements.current_level}"],
            )
            self.smriti.ingest(session_mem)
            print(f"[Smriti] Session memory recorded (sig={sig:.2f})")
        except Exception as e:
            print(f"[Smriti] Error: {e}")

        # Cleanup
        self.wake_word_listener.stop()
        await self.voice.close()

    def _print_status(self):
        acc = self.state_machine.accumulator
        a = self.achievements
        mode = self.support_manager.mode.value
        tw_name = self._last_time_window or "?"
        print(
            f"\n[Status] State: {self.state_machine.state} | Mode: {mode} | "
            f"Window: {tw_name}\n"
            f"         Work: {acc.work_minutes}m | Timepass: {acc.timepass_minutes}m | "
            f"Level: {acc.warning_level} | Frames: {self.frame_count}\n"
            f"         XP: {a.current_xp} (L{a.current_level}) | "
            f"Streak: {a.streaks.daily_work}d | "
            f"Distress: {self.emotional_monitor.get_distress_level()}"
        )


# ── Config persistence ──────────────────────────────────────────────────
AMMA_CONFIG_DIR = Path.home() / ".amma"
AMMA_CONFIG_FILE = AMMA_CONFIG_DIR / "config.json"
AMMA_SESSION_FILE = AMMA_CONFIG_DIR / "session_state.json"


def load_session_state() -> Optional[dict]:
    if AMMA_SESSION_FILE.exists():
        with open(AMMA_SESSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_session_state(data: dict):
    AMMA_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(AMMA_SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def ask_daily_goals(config: AmmaConfig) -> dict:
    """Ask for today's goals if it's a new day, or confirm existing ones."""
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo(config.timezone)
        now_local = datetime.now(tz)
    except Exception:
        now_local = datetime.now()

    today_str = now_local.date().isoformat()
    hour = now_local.hour

    state = load_session_state()
    if state and state.get("date") == today_str and state.get("goals"):
        # Same day, goals exist — confirm or update
        goals = state["goals"]
        hrs = state.get("session_hours")
        hrs_str = f" ({hrs}h target)" if hrs else ""
        print(f"\n  Welcome back. Today's goals{hrs_str}: {', '.join(goals)}")
        try:
            confirm = input("  Still the same? (Enter to keep / type new goals): ").strip()
        except (EOFError, KeyboardInterrupt):
            confirm = ""
        if not confirm:
            print()
            return state
        new_goals = [g.strip() for g in confirm.split(",") if g.strip()]
        state["goals"] = new_goals
        state["goal_asked_at"] = now_local.strftime("%H:%M")
        save_session_state(state)
        print()
        return state

    # New day or no goals — ask fresh
    print("\n" + "━" * 50)
    if hour < 10:
        print(f"  Good morning, {config.nickname}. New day. What are we doing today?")
    elif hour >= 20:
        print(f"  Late session, {config.nickname}. What exactly are you trying to finish?")
    else:
        print(f"  {config.nickname.capitalize()}, what are you working on today?")
    print("━" * 50)

    try:
        goals_raw = input("  Goals (comma-separated, or Enter to skip): ").strip()
    except (EOFError, KeyboardInterrupt):
        goals_raw = ""
    goals = [g.strip() for g in goals_raw.split(",") if g.strip()] if goals_raw else []

    session_hours = None
    try:
        hrs_raw = input("  How many hours do you have? (Enter to skip): ").strip()
        if hrs_raw:
            session_hours = float(hrs_raw)
    except (EOFError, KeyboardInterrupt, ValueError):
        pass
    print()

    new_state = {
        "date": today_str,
        "goals": goals,
        "session_hours": session_hours,
        "goal_asked_at": now_local.strftime("%H:%M"),
    }
    save_session_state(new_state)
    return new_state


def save_user_config(data: dict):
    AMMA_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(AMMA_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[Setup] Config saved to {AMMA_CONFIG_FILE}")


def load_user_config() -> Optional[dict]:
    if AMMA_CONFIG_FILE.exists():
        with open(AMMA_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def run_setup_interview() -> dict:
    """Interactive first-launch setup (Ch 30). Runs in terminal before monitoring starts."""
    print("\n" + "━" * 50)
    print("  Amma अम्मा  —  First Launch Setup")
    print("━" * 50)
    print("  I need to know you before I can watch over you.")
    print("━" * 50 + "\n")

    interview = SetupInterview()
    answers = {}

    # Walk through questions
    q = interview.current_question
    while q:
        key, question = q
        print(f"  {question}")
        if key == "archetype":
            print()
            for k, arch in ARCHETYPES.items():
                print(f"    {k:14s} — {arch.description}")
            print()
        try:
            answer = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[Setup] Setup cancelled. Using defaults.")
            break
        if not answer:
            answer = _setup_defaults(key)
        answers[key] = answer
        q = interview.answer(answer)
        print()

    # Timezone — ask explicitly (not part of SetupInterview questions)
    print("  Your timezone? (e.g. IST, EST, PST, UTC, or IANA like America/New_York)")
    try:
        tz_raw = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        tz_raw = ""
    answers["timezone"] = _normalize_timezone(tz_raw) if tz_raw else "Asia/Kolkata"
    print()

    print("━" * 50)
    print("  Theek hai. I have everything I need.")
    print("  From now on, I am watching.")
    print("━" * 50 + "\n")
    return answers


# Common timezone abbreviation → IANA name
_TZ_ALIASES: dict = {
    "IST": "Asia/Kolkata",
    "EST": "America/New_York",
    "EDT": "America/New_York",
    "CST": "America/Chicago",
    "CDT": "America/Chicago",
    "MST": "America/Denver",
    "MDT": "America/Denver",
    "PST": "America/Los_Angeles",
    "PDT": "America/Los_Angeles",
    "GMT": "UTC",
    "UTC": "UTC",
    "BST": "Europe/London",
    "CET": "Europe/Paris",
    "AEST": "Australia/Sydney",
    "SGT": "Asia/Singapore",
    "JST": "Asia/Tokyo",
    "KST": "Asia/Seoul",
}


def _normalize_timezone(raw: str) -> str:
    """Convert 'EST', 'US/Eastern', etc. to a valid IANA timezone string."""
    import zoneinfo
    raw = raw.strip()
    # Direct IANA lookup first
    try:
        zoneinfo.ZoneInfo(raw)
        return raw
    except Exception:
        pass
    # Try alias map (case-insensitive)
    upper = raw.upper()
    if upper in _TZ_ALIASES:
        return _TZ_ALIASES[upper]
    # Try "US/Eastern" style → "America/New_York" common forms
    for alias, iana in _TZ_ALIASES.items():
        if alias.lower() in raw.lower():
            return iana
    print(f"[Setup] Unknown timezone '{raw}', defaulting to Asia/Kolkata")
    return "Asia/Kolkata"


def _setup_defaults(key: str) -> str:
    defaults = {
        "formal_name": "Beta",
        "nickname": "beta",
        "full_name": "Beta",
        "languages": "English",
        "scold_language": "English",
        "support_language": "English",
        "archetype": "classic",
        "custom_phrase": "",
        "timezone": "Asia/Kolkata",
    }
    return defaults.get(key, "")


def _normalize_archetype(raw: str) -> str:
    """Normalize archetype input: 'Modern all the way!!' → 'modern'."""
    from personality import ARCHETYPES
    raw = raw.strip().lower()
    # Exact match first
    if raw in ARCHETYPES:
        return raw
    # Try first word
    first = raw.split()[0] if raw.split() else raw
    if first in ARCHETYPES:
        return first
    # Fallback: find any archetype key mentioned in the string
    for key in ARCHETYPES:
        if key in raw:
            return key
    return "classic"  # Default


def apply_saved_config(config: AmmaConfig, saved: dict):
    """Apply saved user config dict onto AmmaConfig."""
    if saved.get("formal_name"):
        config.user_formal_name = saved["formal_name"]
    if saved.get("nickname"):
        config.nickname = saved["nickname"]
    if saved.get("full_name"):
        config.full_name = saved["full_name"]
    if saved.get("languages"):
        config.languages = [l.strip() for l in saved["languages"].split(",")]
    if saved.get("scold_language"):
        config.scold_language = saved["scold_language"]
    if saved.get("support_language"):
        config.support_language = saved["support_language"]
    if saved.get("archetype"):
        config.archetype = _normalize_archetype(saved["archetype"])
    if saved.get("custom_phrase"):
        config.custom_phrases["general"] = saved["custom_phrase"]
    if saved.get("timezone"):
        config.timezone = _normalize_timezone(saved["timezone"])
    if saved.get("keyword_path"):
        config.custom_keyword_paths = [saved["keyword_path"]]


async def main():
    load_dotenv()

    config = AmmaConfig(
        gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
        picovoice_access_key=os.environ.get("PICOVOICE_ACCESS_KEY", ""),
        demo_mode="--demo" in sys.argv,
    )

    # ── First-launch setup interview (Ch 30) ─────────────────────────
    saved = load_user_config()
    if saved is None:
        # First launch — run the interview
        user_data = run_setup_interview()
        save_user_config(user_data)
        apply_saved_config(config, user_data)
    else:
        # Returning user — restore saved profile
        apply_saved_config(config, saved)
        print(f"[Setup] Welcome back, {config.user_formal_name}. Profile loaded.")

    # Daily goals — ask fresh each new day, confirm on re-launch
    session_state = ask_daily_goals(config)
    config.goals = session_state.get("goals", [])
    config.session_hours = session_state.get("session_hours")

    # Pre-flight checks
    warnings = startup_checks(config)
    if warnings:
        print("\n⚠️  Startup warnings:")
        for w in warnings:
            print(f"   • {w}")
        print()

    if not config.gemini_api_key:
        print("⚠️  GEMINI_API_KEY not set. Set it in .env or as environment variable.")
        print("   GEMINI_API_KEY=your_key_here")
        sys.exit(1)

    # Single shared client for all Gemini API calls
    client = genai.Client(api_key=config.gemini_api_key)

    session = AmmaSession(config, client)
    await session.start()


if __name__ == "__main__":
    asyncio.run(main())
