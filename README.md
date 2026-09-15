# LiveTranslate 📡
### Real-time YouTube to Tamil Translation using Gemini AI

---

## What it does
- Paste any YouTube video or live stream URL
- Video plays on the LEFT
- Live Tamil translation appears on the RIGHT in real-time

---

## Setup (5 minutes)

### Step 1 — Get your FREE Gemini API Key
1. Go to https://aistudio.google.com
2. Sign in with your Google account
3. Click **"Get API key"** → **"Create API key"**
4. Copy the key (it's FREE, no credit card needed)

### Step 2 — Install dependencies
```bash
# You need Python 3.9+ and ffmpeg installed

# Install ffmpeg (if not installed)
# Mac: brew install ffmpeg
# Ubuntu/Linux: sudo apt install ffmpeg
# Windows: download from https://ffmpeg.org/download.html

# Install Python packages
cd backend
pip install -r requirements.txt
```

### Step 3 — Set your API key
```bash
# In the backend folder, create a .env file:
cp ../.env.example .env

# Edit .env and paste your Gemini API key:
# GEMINI_API_KEY=AIzaSy...your_key_here
```

### Step 4 — Run the backend
```bash
cd backend
uvicorn main:app --reload
```
You should see: `Uvicorn running on http://127.0.0.1:8000`

### Step 5 — Open the frontend
- Open `frontend/index.html` in your browser (just double-click it)
- Paste a YouTube URL
- Click **▶ Start**
- Watch the Tamil translation appear on the right! 🎉

---

## Demo URLs to try
- BBC News Live: https://www.youtube.com/watch?v=w_Ma8oQLmSM
- CNN Live: https://www.youtube.com/watch?v=H3pEEMFxxRI
- Any English YouTube video works too!

---

## Tech Stack
| Layer | Technology |
|-------|-----------|
| Video | YouTube iframe embed |
| Audio extraction | yt-dlp + ffmpeg |
| ASR | Google Gemini 2.5 Flash |
| Translation | Gemini 2.5 Flash (same model) |
| Streaming | Server-Sent Events (SSE) |
| Backend | Python FastAPI |
| Frontend | Vanilla HTML/CSS/JS |

---

## Project Structure
```
livetranslate/
├── backend/
│   ├── main.py          ← FastAPI server
│   └── requirements.txt
├── frontend/
│   └── index.html       ← Full UI (open this in browser)
├── .env.example
└── README.md
```
