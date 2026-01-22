# PowerApps Localport Bridge

A comprehensive solution for integrating Power Apps with local AI services for speech recognition, transcription, and **English pronunciation teaching**. This project provides Docker-based backends that can be coupled to Power Apps via Power Automate Desktop (PAD) bridges.

## Overview

This repository contains two main systems:

1. **ASR Data Collection** - Whisper-based audio transcription for Power Apps
2. **Pronunciation Teaching System** - Real-time English vowel feedback with HuggingFace models

Both systems share the same architecture pattern:

```
Power Apps → Power Automate Cloud → Power Automate Desktop → PowerShell Bridge → FastAPI → AI Models
```

---

## 🎤 Pronunciation Teaching System (NEW)

A complete English pronunciation training system with real-time vowel feedback. Students upload XLSX exercise files and receive instant feedback on their pronunciation using state-of-the-art speech recognition models.

### Features

- **Vowel-Specific Feedback**: Identifies exactly which vowels need improvement
- **XLSX Exercise Support**: Upload sentence lists with auto-generated IPA phonemes
- **Dual Frontend**: React web GUI + Power Apps integration
- **Real-time Analysis**: WhisperX word-level alignment for precise error location
- **Configurable**: CPU/GPU mode, model selection via environment variables

### Models Used

| Model | Purpose | Source |
|-------|---------|--------|
| `facebook/wav2vec2-lv-60-espeak-cv-ft` | IPA phoneme extraction | HuggingFace |
| `whisperx` | Word-level forced alignment | GitHub |
| `openai-whisper` (medium.en) | Speech-to-text | OpenAI |
| `g2p-en` | Text-to-phoneme for auto-IPA | PyPI |

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Power Apps / React Web UI                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Pronunciation API (:8000)                  │
│  POST /transcribe  → PowerApps-compatible                   │
│  POST /assess      → Full vowel assessment                  │
│  POST /exercises/upload → XLSX with sentences               │
└─────────────────────────────────────────────────────────────┘
              │                              │
              ▼                              ▼
┌─────────────────────────┐    ┌─────────────────────────────┐
│   Whisper ASR (:9001)   │    │   Phoneme Service (:8001)   │
│   Speech-to-text        │    │   wav2vec2 + WhisperX       │
└─────────────────────────┘    └─────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- (Optional) NVIDIA GPU with Docker GPU support for faster inference

### 1. Clone Repository

```bash
git clone <repository-url>
cd PowerApps-Localport-Bridge
```

### 2. Start Pronunciation System

```bash
cd ASR_DataCollection/C_Docker/pronunciation-system

# Configure environment
cp .env.example .env

# Edit .env if needed:
# DEVICE=cpu        (or cuda for GPU)
# WHISPER_MODEL=medium.en
# LOG_LEVEL=INFO

# Start all services
docker compose up -d --build

# Watch startup logs (models take 2-5 minutes to load on first run)
docker compose logs -f
```

### 3. Access the Application

| Service | URL | Description |
|---------|-----|-------------|
| Web UI | http://localhost:3000 | React pronunciation trainer |
| API Docs | http://localhost:8000/docs | Swagger/OpenAPI documentation |
| Health Check | http://localhost:8000/health | Service status |

### 4. Upload Exercise XLSX

Create an Excel file with:

| Column A (Required) | Column B (Optional) | Column C (Optional) |
|---------------------|---------------------|---------------------|
| Sentence text | Expected IPA | Focus vowels |
| Hello, how are you? | | ə, oʊ |
| The cat sat on the mat. | | æ |

- Column B auto-generates if empty using g2p-en
- Column C specifies which vowels to emphasize

Upload via web UI or API:
```bash
curl -X POST http://localhost:8000/exercises/upload -F "file=@exercises.xlsx"
```

---

## 📱 Power Apps Integration

### For Basic Transcription (Existing)

Use `ASR_DataCollection/B_PAD/Scripts/Whisper_Bridge.ps1`:

```powershell
# PAD variables:
# %FileName%, %FolderName%, %Base64Audio%
```

### For Pronunciation Assessment (New)

Use `ASR_DataCollection/B_PAD/Scripts/Pronunciation_Bridge.ps1`:

```powershell
# PAD variables:
# %FileName%     - Audio file name
# %Base64Audio%  - Base64-encoded WAV audio
# %ExpectedText% - Sentence student should read
# %Mode%         - "transcribe" or "assess"

# Returns JSON with:
# - transcription
# - overall_score_pct (e.g., "85.2%")
# - vowel_score_pct
# - focus_areas
# - vowel_errors_count
```

### Power Automate Cloud Flow

Configure your PAC flow to pass:
1. `text` → FileName
2. `text_1` → FolderName  
3. `text_2` → Base64Audio (header stripped in Power Apps)
4. `text_3` → ExpectedText (for assessment mode)

---

## 🎯 English Vowels Assessed

### Monophthongs
| IPA | Name | Example | Difficulty |
|-----|------|---------|------------|
| ɪ | short i | b**i**t | High |
| ɛ | short e | b**e**t | Medium |
| æ | short a | b**a**t | High |
| ʌ | short u | b**u**t | High |
| ʊ | short oo | b**oo**k | High |
| ə | schwa | **a**bout | High |
| i | long ee | b**ea**t | Low |
| u | long oo | b**oo**t | Low |

### Diphthongs
| IPA | Name | Example |
|-----|------|---------|
| eɪ | long a | b**ai**t |
| oʊ | long o | b**oa**t |
| aɪ | long i | b**i**te |
| aʊ | ow | b**ou**t |
| ɔɪ | oy | b**oy** |

---

## 📁 Project Structure

```
PowerApps-Localport-Bridge/
├── README.md                          # This file
├── ASR_DataCollection/
│   ├── A_PowerApps_flow/              # Power Platform solution files
│   │   └── Workflows/                 # PAC flow definitions
│   ├── B_PAD/
│   │   └── Scripts/
│   │       ├── Whisper_Bridge.ps1     # Original transcription bridge
│   │       ├── Pronunciation_Bridge.ps1  # NEW: Assessment bridge
│   │       ├── whisper_api.py         # Original FastAPI
│   │       └── Deep_whisper_api.py
│   ├── C_Docker/
│   │   ├── High Security docker container_3models..txt
│   │   └── pronunciation-system/      # NEW: Complete Docker stack
│   │       ├── docker-compose.yml
│   │       ├── .env.example
│   │       ├── README.md
│   │       ├── pronunciation-api/     # FastAPI orchestration
│   │       ├── phoneme-service/       # wav2vec2 + WhisperX
│   │       └── frontend/              # React + Vite + Nginx
│   └── Fast API/
│       └── whisper_api.py
└── RLHL_TrainingAgent/                # Separate project
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Options |
|----------|---------|---------|
| `DEVICE` | cpu | `cpu`, `cuda` |
| `GPU_COUNT` | 0 | `0`, `1`, `2`... |
| `WHISPER_MODEL` | medium.en | `tiny`, `base`, `small`, `medium`, `medium.en`, `large`, `large-v2` |
| `LOG_LEVEL` | INFO | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Ports

| Service | Port | Configurable |
|---------|------|--------------|
| Frontend (Nginx) | 3000 | Edit docker-compose.yml |
| Pronunciation API | 8000 | Edit docker-compose.yml |
| Phoneme Service | 8001 | Internal only |
| Whisper ASR | 9001 | Internal only |

---

## 🔧 Development

### Run Without Docker

```bash
# Terminal 1: Phoneme Service
cd ASR_DataCollection/C_Docker/pronunciation-system/phoneme-service
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001

# Terminal 2: Pronunciation API
cd ASR_DataCollection/C_Docker/pronunciation-system/pronunciation-api
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 3: Frontend
cd ASR_DataCollection/C_Docker/pronunciation-system/frontend
npm install
npm run dev
```

### Rebuild Single Service

```bash
cd ASR_DataCollection/C_Docker/pronunciation-system
docker compose up -d --build phoneme-service
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service with timestamps
docker compose logs -f --timestamps phoneme-service
```

---

## 🐛 Troubleshooting

### Models Not Loading
- First startup downloads ~2-5GB of models
- Check logs: `docker compose logs phoneme-service`
- Ensure sufficient disk space and network connectivity

### GPU Not Detected
```bash
# Verify NVIDIA Docker runtime
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.1-base-ubuntu22.04 nvidia-smi
```

### Audio Recording Not Working
- Check browser microphone permissions
- Ensure HTTPS or localhost (required for MediaRecorder API)
- Test microphone in system settings

### PowerApps Connection Issues
- Verify FastAPI is running: `curl http://127.0.0.1:8000/health`
- Check PAD debug log: `C:\Users\Admin\AppData\Local\Temp\Pronunciation_Temp\pad_debug.txt`
- Ensure Base64 audio header is stripped in Power Apps before sending

---

## 📊 API Reference

### POST /transcribe (PowerApps Compatible)

```json
// Request
{
  "file_name": "audio_001",
  "format": "txt",
  "base64_audio": "UklGRi..."
}

// Response
{
  "file_name": "audio_001",
  "transcription": "Hello world"
}
```

### POST /assess (Pronunciation Assessment)

```json
// Request
{
  "file_name": "audio_001",
  "base64_audio": "UklGRi...",
  "expected_text": "Hello, how are you today?"
}

// Response
{
  "file_name": "audio_001",
  "transcription": "Hello how are you today",
  "phoneme_assessment": {
    "overall_score": 0.847,
    "vowel_score": 0.812,
    "vowel_errors": [
      {
        "position": 2,
        "expected": "aʊ",
        "actual": "oʊ",
        "error_type": "substitution",
        "word": "how",
        "timestamp_ms": 450
      }
    ],
    "focus_areas": [
      "/aʊ/ (ow) - as in 'bout' - 1 error(s)"
    ],
    "total_vowels": 8,
    "correct_vowels": 7
  },
  "processing_time_ms": 2340
}
```

### POST /exercises/upload

```bash
curl -X POST http://localhost:8000/exercises/upload \
  -F "file=@my_exercises.xlsx"
```

---

## 📜 License

MIT License - See LICENSE file for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📞 Support

For issues related to:
- **Power Apps integration**: Check PAD debug logs
- **Docker/Models**: Open a GitHub issue with `docker compose logs` output
- **Frontend**: Check browser console for errors
