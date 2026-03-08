# Amma अम्मा — Architecture

Two views of the system. The flowchart shows how agents talk to each other. The mindmap shows every feature, grouped by what it does.

---

## Orchestration Flow

7 async loops run in parallel via `asyncio.gather()`. They share state through the memory layer and communicate via queues and direct calls. The orchestrator (`AmmaSession` in `main.py`) owns the session lifecycle.

```mermaid
flowchart TD
    USER(("👤 User"))

    subgraph INPUTS["⚡ Input Sensors — 7 loops via asyncio.gather()"]
        direction LR
        VIS["📺 vision_loop\nscreenshot every 5s\nmss + win32gui"]
        MIC["🎙️ wake_word_loop\nPorcupine — Hi-Amma.ppn\nfully offline"]
        CLI["⌨️ command_listener\nbreak · back · support\nquit · demo · stuck"]
    end

    subgraph GEMINI["🤖 Gemini Models"]
        direction TB
        GC["Gemini 3 Flash\nVision → WORK · GREY · TIMEPASS · NUCLEAR"]
        GSTT["Gemini 2.5 Flash\nSTT transcription + contextual response"]
        GTTS["Gemini 2.5 Flash Preview TTS\nExpressive voice synthesis → pygame PCM"]
    end

    subgraph MEM["💾 Memory Layer"]
        direction LR
        ACC["⏱ Accumulator\nwork/timepass wall-clock\ndebounce · gap cap · 12h cap"]
        PAT["🕳 Pattern Tracker\nblack hole detection\nrepeat app frequency"]
        CACHE["📋 Ruling Cache\napp → classification\nsession-scoped fast path"]
        SMR["🧠 Smriti स्मृति\nlong-term session memory\nsignificance scoring + excuse archive"]
    end

    subgraph AGENTS["🎯 Decision Agents"]
        direction LR
        FSM["🔀 State Machine\n5-level escalation FSM\nsnap-back · NUCLEAR · debounce"]
        SUPP["💜 Support Mode\ndistress · crisis\nwellbeing protocol"]
        BRK["☕ Break Manager\n15/30/60m check-ins\nCtrl+Shift+B hotkey"]
        EMO["😔 Emotional Monitor\nburnout · unusual hours\ntab-switch cluster signals"]
        MEN["📚 Mentor Agent\nstuck detection · rubber duck\nskill gaps · I Looked It Up"]
        TOD["🕐 Time of Day\nmorning/peak/slump\nlate-night/alarm windows"]
        SPD["🪔 Special Days\nfestivals — all users\nexams · IPL — India only"]
        CNT["▶️ Content Reactions\ntutorial · course · podcast\nnotes check · passive warning"]
        TSC["📊 Trust Score\n5 behavioral signals\npatience calibration"]
        GAM["🏆 Gamification\nXP · 50 levels · 16 badges\nstreaks · anti-gaming guards"]
    end

    subgraph OUT["📢 Output Layer"]
        direction LR
        TTS_OUT["🔊 Voice Output\nGemini TTS → WAV → pygame\nvolume scales with level L0–L6"]
        OVL["🪟 Glass Overlay\nPyQt6 · Windows acrylic blur\nclassification · timers · last line"]
        RCP["🧾 Receipt Card\nPillow PNG · grade S–F\nefficiency · trust · XP verdict"]
    end

    subgraph EXT["🌐 External"]
        direction LR
        SRP["🔍 Serper.dev\ngrey zone web context\nI Looked It Up explanations"]
        CB["☁️ Cloud Brain\nFastAPI WebSocket server\ncross-device state sync"]
        PH["📱 Phone App\nExpo React Native\nlive status + remote commands"]
    end

    USER -->|screen activity| VIS
    USER -->|"Hi Amma"| MIC
    USER -->|types| CLI

    VIS -->|frame queue| GC
    MIC -->|"wake → record → transcribe"| GSTT
    GSTT -->|response text| GTTS
    GTTS --> TTS_OUT

    GC -->|classification| CACHE
    CACHE --> AGENTS
    GC -->|classification| MEM
    MEM <-->|session context| AGENTS

    CLI --> AGENTS
    AGENTS -->|dialogue line + volume| GTTS
    AGENTS --> OVL
    AGENTS -->|session end| RCP
    AGENTS -->|web lookup| SRP
    SRP -->|explanation text| GTTS

    AGENTS --> CB
    CB <--> PH
    PH -->|commands| CLI
```

---

## Feature Map

Every feature Amma has, grouped by what it does.

```mermaid
mindmap
  root((Amma अम्मा))
    👁️ Perception
      Screenshot every 5s
      Gemini 3 Flash vision classifier
      WORK · GREY · TIMEPASS · NUCLEAR
      Grey zone 30s timeout
      Session ruling cache fast path
    🎙️ Voice
      Hi-Amma wake word — offline
      Mic recording with VAD
      Gemini 2.5 Flash STT
      Gemini 2.5 Flash contextual response
      Gemini 2.5 Flash Preview TTS
      Code-switches EN · HI · KN · MR
    ⚡ Escalation
      5-level warning FSM
      Snap-back praise on return
      NUCLEAR — full name — 30s repeat
      Debounce 30s between levels
      Black hole app → skip to L3
    🧘 Modes
      Guard — full monitoring
      Support — wellbeing first
      Break — timer + 15/30/60m check-ins
      Mentor — rubber duck protocol
    🧠 Intelligence
      Pattern tracker — black holes
      Emotional monitor — burnout · crisis
      Stuck detection — tab-switch · delete clusters
      Skill gap tracker — repeat searches
      I Looked It Up — Serper web fetch
      Content reactions — tutorial · course · podcast
    ⏰ Time & Culture
      Time of day — 5 windows
      3pm slump detection
      Alarm mode after 2am
      Special days — Indian calendar
      Festivals fire for all users
      Exams and IPL — India only via timezone
    💾 Memory
      Accumulator — wall-clock work/timepass
      Smriti — long-term session memory
      Significance scoring
      Excuse archive
      Session ruling cache
    📊 Scoring
      Trust score — 5 behavioral signals
      XP system — 50 levels
      16 badges
      Streak system with 2 grace tokens
      Anti-gaming safeguards
    📢 Output
      Gemini TTS voice
      PyQt6 glass overlay — Windows acrylic blur
      Session receipt card PNG — S to F grade
      25+ dialogue pools — no repeats
      Volume scales per escalation level
    🌐 Cross-device
      Cloud Brain — FastAPI WebSocket
      Phone app — Expo React Native
      Break/back commands from phone
    🔧 Setup
      First-run setup interview
      6 personality archetypes
      Timezone-aware — India vs diaspora
      Saved profile — config.json
```

---

*For setup instructions, see [SETUP.md](SETUP.md). For the README overview, see [README.md](README.md).*
