import os
import asyncio
import subprocess
import threading
import queue
import tempfile
import wave
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

translation_queue = queue.Queue()
stop_event = threading.Event()
active_process = None


class StreamRequest(BaseModel):
    youtube_url: str
    target_language: str = "Tamil"


def extract_and_translate(youtube_url: str, target_language: str):
    global active_process, stop_event
    stop_event.clear()

    CHUNK_SECONDS = 15
    SAMPLE_RATE = 16000
    CHANNELS = 1
    SAMPLE_WIDTH = 2
    CHUNK_SIZE = SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH * CHUNK_SECONDS

    try:
        yt_cmd = [
            "yt-dlp",
            "-f", "bestaudio",
            "--no-playlist",
            "-o", "-",
            "--quiet",
            youtube_url
        ]

        ff_cmd = [
            "ffmpeg",
            "-i", "pipe:0",
            "-f", "s16le",
            "-ar", str(SAMPLE_RATE),
            "-ac", str(CHANNELS),
            "-loglevel", "quiet",
            "pipe:1"
        ]

        yt_process = subprocess.Popen(yt_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        ff_process = subprocess.Popen(ff_cmd, stdin=yt_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

        active_process = (yt_process, ff_process)

        buffer = b""

        while not stop_event.is_set():
            chunk = ff_process.stdout.read(4096)
            if not chunk:
                break

            buffer += chunk

            while len(buffer) >= CHUNK_SIZE:
                audio_chunk = buffer[:CHUNK_SIZE]
                buffer = buffer[CHUNK_SIZE:]

                if stop_event.is_set():
                    break

                # ✅ Save temp WAV
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp_path = tmp.name
                    with wave.open(tmp_path, 'wb') as wf:
                        wf.setnchannels(CHANNELS)
                        wf.setsampwidth(SAMPLE_WIDTH)
                        wf.setframerate(SAMPLE_RATE)
                        wf.writeframes(audio_chunk)

                try:
                    with open(tmp_path, "rb") as f:
                        audio_bytes = f.read()

                    # ✅ RETRY LOGIC (CORRECT PLACE)
                    for attempt in range(3):
                        try:
                            response = client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=[
                                    {
                                        "role": "user",
                                        "parts": [
                                            {
                                                "inline_data": {
                                                    "mime_type": "audio/wav",
                                                    "data": audio_bytes
                                                }
                                            },
                                            {
                                                "text": f"You are a live translator. Convert spoken English audio into {target_language}. Return ONLY translated text."
                                            }
                                        ]
                                    }
                                ]
                            )

                            text = response.text.strip()

                            if text:
                                translation_queue.put(text)

                            time.sleep(3)  # ✅ rate limit protection
                            break

                        except Exception as e:
                            if "429" in str(e):
                                print("Rate limited. Retrying...")
                                time.sleep(5)
                            else:
                                print(f"Gemini error: {e}")
                                break

                except Exception as e:
                    print(f"Processing error: {e}")

                finally:
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass

    except Exception as e:
        print(f"Stream error: {e}")
        translation_queue.put(f"[Error: {str(e)}]")

    finally:
        try:
            if active_process:
                active_process[0].kill()
                active_process[1].kill()
        except:
            pass

        translation_queue.put("[STREAM_END]")


@app.post("/api/start")
async def start_stream(req: StreamRequest):
    global translation_queue

    while not translation_queue.empty():
        translation_queue.get_nowait()

    thread = threading.Thread(
        target=extract_and_translate,
        args=(req.youtube_url, req.target_language),
        daemon=True
    )
    thread.start()

    return {"status": "started"}


@app.get("/api/stream")
async def stream_translations():
    async def event_generator():
        loop = asyncio.get_event_loop()

        while True:
            try:
                text = await loop.run_in_executor(None, translation_queue.get, True, 1.0)

                if text == "[STREAM_END]":
                    yield "data: [DONE]\n\n"
                    break

                yield f"data: {text}\n\n"

            except queue.Empty:
                yield "data: [PING]\n\n"

            except Exception as e:
                yield f"data: [Error: {e}]\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/api/stop")
async def stop_stream():
    global active_process

    stop_event.set()

    if active_process:
        try:
            active_process[0].kill()
            active_process[1].kill()
        except:
            pass

        active_process = None

    return {"status": "stopped"}


@app.get("/")
async def root():
    return {"message": "LiveTranslate API is running 🚀"}