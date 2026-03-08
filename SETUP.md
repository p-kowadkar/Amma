# Amma — Setup Guide

## Requirements

- Python 3.11+
- Node.js 20+ (for phone app)
- Windows 10/11 (Linux/macOS supported with minor fallbacks)
- A Gemini API key (everything else is optional)

---

## 1. Python Setup

```powershell
# Clone or navigate to the project
cd D:\My-Projects\Amma

# Install dependencies
pip install -r requirements.txt

# On Windows, pywin32 is included in requirements.txt
# If it fails separately: pip install pywin32
```

---

## 2. Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

```powershell
copy .env.example .env
```

**Minimum to run (everything else is optional):**

```env
GEMINI_API_KEY=your_key_here
```

Get your Gemini API key at: https://aistudio.google.com/app/apikey

**Optional keys (features degrade gracefully without them):**

| Variable | What it enables | Get it from |
|---|---|---|
| `SERPER_API_KEY` | Grey zone web search + "I Looked It Up" | https://serper.dev |
| `PICOVOICE_ACCESS_KEY` | "Hey Amma" wake word | https://console.picovoice.ai |
| `REDIS_URL` | Cloud Brain session persistence | https://upstash.com |
| `SUPABASE_URL` + `SUPABASE_KEY` | Persistent gamification + Smriti | https://supabase.com |

---

## 3. First Run

```powershell
python main.py
```

On first launch, Amma will ask you 9 questions to set up your profile — your name, languages, archetype, and timezone. This saves to `~/.amma/config.json` and never runs again.

Timezone matters: enter `IST`, `EST`, `PST`, etc. or a full IANA name like `America/New_York`. Indian exam seasons and IPL only activate if you're in India.

```powershell
# Demo mode (enables time-skip commands for testing/presenting)
python main.py --demo
```

---

## 4. Cloud Brain (Optional — needed for phone app)

The Cloud Brain is a FastAPI WebSocket server that syncs state across devices.

```powershell
# Run locally
uvicorn cloud_brain.server:app --host 0.0.0.0 --port 8080

# Or with auto-reload during development
uvicorn cloud_brain.server:app --reload --port 8080
```

### Deploy to Fly.io

```powershell
# Install Fly CLI
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"

# Login
fly auth signup

# Create Dockerfile (already included in project root if you followed setup)
fly launch --name amma-brain

# Set secrets
fly secrets set GEMINI_API_KEY=your_key_here

# Deploy
fly deploy

# Add Redis for persistence (optional)
fly redis create --name amma-redis
# This sets REDIS_URL automatically
```

---

## 5. Phone App (Optional)

```powershell
cd phone

# Install dependencies
npm install

# Run on device/emulator
npx expo start
```

Then scan the QR code with the Expo Go app, or press `a` for Android emulator / `i` for iOS simulator.

**Configure the Cloud Brain URL:**
In the phone app, tap the ⚙️ icon and enter your Cloud Brain WebSocket URL:
- Local: `ws://YOUR_PC_IP:8080`
- Deployed: `wss://amma-brain.fly.dev`

---

## 6. Wake Word (Optional)

To enable hands-free **"Hi Amma"** activation:

1. Go to https://console.picovoice.ai — create a free account
2. Get your Access Key — add to `.env`:
   ```env
   PICOVOICE_ACCESS_KEY=your_key_here
   ```
3. Train a custom keyword (e.g. "Hi-Amma") in the Picovoice Console
4. Download the `.ppn` file → extract the ZIP into the project folder
   (e.g. `D:\My-Projects\Amma\Hi-Amma\Hi-Amma_en_windows_v4_0_0.ppn`)
5. Add the keyword path to `~/.amma/config.json`:
   ```json
   {
     "keyword_path": "Hi-Amma/Hi-Amma_en_windows_v4_0_0.ppn"
   }
   ```
6. Install audio packages (if not already via requirements.txt):
   ```powershell
   pip install pvporcupine pyaudio
   ```

Once active: say **"Hi Amma"** → Amma acknowledges → speak freely → she transcribes, understands, and responds with full session context.

---

## 7. Google Calendar Integration (Optional)

1. Go to https://console.cloud.google.com
2. Create a project → Enable Google Calendar API
3. Create OAuth 2.0 credentials (Desktop app type)
4. Download `credentials.json` → place in `~/.amma/`
5. Install:
   ```powershell
   pip install google-auth-oauthlib google-api-python-client
   ```
6. Add to `.env`:
   ```env
   GOOGLE_CALENDAR_CREDENTIALS=~/.amma/credentials.json
   ```

---

## 8. Spotify Integration (Optional)

1. Go to https://developer.spotify.com/dashboard → Create app
2. Add `http://localhost:8888/callback` as redirect URI
3. Install: `pip install spotipy`
4. Add to `.env`:
   ```env
   SPOTIFY_CLIENT_ID=your_id
   SPOTIFY_CLIENT_SECRET=your_secret
   ```

---

## 9. Supabase Persistence (Optional)

For gamification and Smriti memory to persist across sessions:

1. Create a free project at https://supabase.com
2. Install: `pip install supabase`
3. Add to `.env`:
   ```env
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your_anon_key
   ```
4. Run the schema SQL from `Vol XV` of the spec (pgvector tables for Smriti)

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+Shift+B` | Toggle break mode (global hotkey) |
| Double-click overlay | Collapse / expand the glass widget |
| Drag overlay | Move it anywhere on screen |

---

## Troubleshooting

**`GEMINI_API_KEY not set`** — Create `.env` in the project root with your key.

**`pywin32 not found`** — Run `pip install pywin32` then `python Scripts/pywin32_postinstall.py -install` from your Python directory.

**`pygame audio init failed`** — Amma will fall back to text-only. Install proper audio drivers or try `pip install pygame --upgrade`.

**`PyQt6` import error** — Run `pip install PyQt6`. The overlay gracefully degrades if this fails.

**Screen capture shows wrong monitor** — Edit `monitor_index` in your `~/.amma/config.json` (0 = primary).

**Wake word not detecting** — Ensure `pyaudio` is installed and a microphone is accessible. Porcupine needs a valid `.ppn` file for custom words.

---

## Development

```powershell
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_phase1.py -v

# Check a specific module standalone
python trust_score.py
python special_days.py
python receipt_card.py
```

Tests: 301 passing across 6 phases. All modules have standalone test coverage.

---

## Project Structure

```
D:\My-Projects\Amma\
├── main.py                  # Entry point
├── requirements.txt
├── .env.example
├── SETUP.md                 # This file
├── README.md
│
├── [30+ Python modules]     # See README.md architecture section
│
├── cloud_brain/             # FastAPI WebSocket server
├── social/                  # Social layer models
├── phone/                   # Expo React Native app
├── tests/                   # 301 tests
├── reports/                 # Implementation status
└── Plan/                    # 16-volume spec docs
```
