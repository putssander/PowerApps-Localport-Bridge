# whisper_api.py
# Run with:
#   uvicorn whisper_api:app --host 0.0.0.0 --port 8000

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
import base64
import requests

app = FastAPI()

# Whisper HTTP endpoint in Docker
WHISPER_URL = "http://127.0.0.1:9000/asr?encode=true&task=transcribe&language=en&output=srt"

# Local folder for audio + transcript
BASE_DIR = Path(r"C:\Users\Admin\AppData\Local\Temp\Whisper_Temp")
BASE_DIR.mkdir(parents=True, exist_ok=True)


class AudioRequest(BaseModel):
    file_name: str          # e.g. Metadata_2025_JadeSmith_20251202_U1S1_00001
    format: str | None = None
    base64_audio: str       # clean Power Apps base64 audio (no header)


@app.post("/transcribe")
def transcribe_audio(payload: AudioRequest):
    print(f"DEBUG FastAPI: got request for {payload.file_name}")

    # 1) Decode Power Apps base64
    try:
        audio_bytes = base64.b64decode(payload.base64_audio)
    except Exception as e:
        text = f"DEBUG: Invalid base64 audio: {e}"
        return {"file_name": payload.file_name, "transcription": text}

    # 2) Build filenames
    base_name = payload.file_name
    audio_path = BASE_DIR / f"{base_name}.wav"
    txt_path = BASE_DIR / f"{base_name}.txt"

    # 3) Save audio locally
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    # 4) Send audio to Whisper server (use audio_file like the old script)
    try:
        with open(audio_path, "rb") as f:
            files = {"audio_file": (audio_path.name, f, "audio/wav")}
            resp = requests.post(WHISPER_URL, files=files, timeout=300)
    except requests.RequestException as e:
        text = f"DEBUG: Whisper server error: {e}"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        return {"file_name": base_name, "transcription": text}

    print(f"DEBUG FastAPI: Whisper status={resp.status_code}")
    raw = resp.text

    # 5) Try JSON, fall back to raw text/SRT
    if resp.status_code == 200:
        try:
            data = resp.json()
            text = data.get("text") or data.get("transcription") or raw
        except ValueError:
            text = raw
    else:
        text = f"DEBUG: Whisper responded {resp.status_code}: {raw[:200]}"

    # 6) Save transcript or debug text
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)

    # 7) Return to PAC → Power Apps
    return {"file_name": base_name, "transcription": text}
