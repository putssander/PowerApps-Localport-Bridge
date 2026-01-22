# Pronunciation Teaching System

English pronunciation training system with real-time vowel feedback. Students can practice sentences from XLSX exercise files and receive instant feedback on their vowel pronunciation using state-of-the-art speech recognition models.

## Features

- 🎤 **Real-time Audio Recording** - Record your pronunciation directly in the browser
- 📊 **Instant Vowel Feedback** - Get immediate feedback on vowel pronunciation accuracy
- 📝 **Word-by-Word Highlighting** - See which words need improvement at a glance
- 💡 **Practical Tips** - Receive actionable pronunciation tips with example words
- 📁 **XLSX Exercise Import** - Upload custom exercise files or use the example
- 🔌 **PowerApps Compatible** - API designed for integration with Power Automate Desktop

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    Frontend (React/Nginx)                      │
│                     http://localhost:3000                      │
│  • Audio Recording    • Waveform Visualization                │
│  • XLSX Upload        • Vowel Feedback Dashboard              │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                  Pronunciation API (FastAPI)                   │
│                     http://localhost:8000                      │
│  POST /transcribe  → PowerApps-compatible transcription       │
│  POST /assess      → Full pronunciation assessment            │
│  POST /exercises/upload → XLSX exercise upload                │
│  GET  /exercises   → List available exercises                 │
│  GET  /exercises/example/download → Download example XLSX     │
│  GET  /health      → Health check all services                │
└────────────────────────────────────────────────────────────────┘
                    │                       │
                    ▼                       ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│       Whisper ASR        │    │     Phoneme Service      │
│   http://localhost:9002  │    │   http://localhost:8001  │
│                          │    │                          │
│  • Speech-to-text        │    │  • wav2vec2 phoneme      │
│  • English optimized     │    │    extraction (IPA)      │
│  • JSON/TXT output       │    │  • Vowel assessment      │
└──────────────────────────┘    └──────────────────────────┘
```

## Models Used

| Model | Purpose | Source |
|-------|---------|--------|
| `facebook/wav2vec2-lv-60-espeak-cv-ft` | Direct IPA phoneme extraction | HuggingFace |
| `openai-whisper` (medium.en) | Speech-to-text transcription | OpenAI |
| `g2p-en` | Text-to-phoneme for expected IPA | PyPI |

## Quick Start

### 1. Start Services

```bash
cd ASR_DataCollection/C_Docker/pronunciation-system

# Build and start all services
docker compose up -d --build

# Watch logs
docker compose logs -f

# Check health
curl http://localhost:8000/health
```

### 2. Verify All Services Running

```bash
docker compose ps
```

Expected output:
```
NAME                     STATUS          PORTS
phoneme-service          Up (healthy)    127.0.0.1:8001->8001/tcp
pronunciation-api        Up (healthy)    127.0.0.1:8000->8000/tcp
pronunciation-frontend   Up (healthy)    127.0.0.1:3000->80/tcp
whisper-asr              Up (healthy)    127.0.0.1:9002->9000/tcp
```

### 3. Access the Application

| Service | URL | Description |
|---------|-----|-------------|
| **Web UI** | http://localhost:3000 | React pronunciation trainer |
| **API Docs** | http://localhost:8000/docs | Interactive API documentation |
| **Health Check** | http://localhost:8000/health | Service health status |
| **Example File** | http://localhost:8000/exercises/example/download | Download example XLSX |

## Using the Web Interface

### 1. Upload an Exercise

1. Go to **Upload** tab
2. Click **Download Example File** to get a template
3. Modify the file with your own sentences (or use as-is)
4. Drag & drop or click to upload your XLSX file

### 2. Practice Pronunciation

1. Go to **Practice** tab
2. Select a sentence from the exercise list
3. Click the microphone button to record
4. Speak the sentence clearly
5. Click stop when finished
6. Review your feedback

### 3. Understanding Feedback

- **Green words** ✓ - Pronounced correctly
- **Red words** ✗ - Need improvement (hover for details)
- **How to Improve** section shows specific vowel sounds to practice
- **Detailed Errors** (collapsible) shows phoneme-level analysis

## XLSX Exercise Format

An example file is included: `examples/pronunciation_exercises_example.xlsx`

### Required Format

| Column A (Required) | Column B (Optional) | Column C (Optional) |
|---------------------|---------------------|---------------------|
| **Sentence text** | Expected IPA phonemes | Focus vowels |
| The cat sat on the mat. | *(auto-generated)* | short-a |
| Please eat the green peas. | *(auto-generated)* | long-ee |
| Ship or sheep? | *(auto-generated)* | short-i, long-ee |

### Column Details

- **Column A** - Sentence (Required): The English sentence students will practice
- **Column B** - IPA Phonemes (Optional): Leave empty for automatic generation using g2p-en
- **Column C** - Focus Vowels (Optional): Specify which vowels to emphasize (comma-separated)

### Example Exercises by Vowel Type

#### Short Vowels
| Sentence | Focus |
|----------|-------|
| The cat sat on the mat. | short-a (æ) |
| Did you see the big ship? | short-i (ɪ) |
| The red hen met ten men. | short-e (ɛ) |
| The bus was stuck in mud. | short-u (ʌ) |

#### Long Vowels
| Sentence | Focus |
|----------|-------|
| Please eat the green peas. | long-ee (i) |
| The goat rode the boat home. | long-o (oʊ) |
| Sue knew the blue moon was cool. | long-oo (u) |

#### Diphthongs
| Sentence | Focus |
|----------|-------|
| My kite flies high in the sky. | long-i (aɪ) |
| How now brown cow. | ow (aʊ) |
| The boy enjoyed his toy. | oy (ɔɪ) |

#### Minimal Pairs (Contrast Practice)
| Sentence | Focus |
|----------|-------|
| Ship or sheep? | short-i vs long-ee |
| Full or fool? | short-oo vs long-oo |
| Bad or bed? | short-a vs short-e |

## API Usage

### Upload Exercise XLSX

```bash
curl -X POST http://localhost:8000/exercises/upload \
  -F "file=@examples/pronunciation_exercises_example.xlsx"
```

Response:
```json
{
  "exercise_id": "a1b2c3d4",
  "message": "Exercise uploaded successfully",
  "sentence_count": 21,
  "auto_generated_phonemes": 20
}
```

### List Exercises

```bash
curl http://localhost:8000/exercises
```

### Transcribe Audio (PowerApps Compatible)

```bash
curl -X POST http://localhost:8000/transcribe \
  -H "Content-Type: application/json" \
  -d '{"file_name": "recording", "base64_audio": "<base64-wav-data>"}'
```

### Full Pronunciation Assessment

```bash
curl -X POST http://localhost:8000/assess \
  -H "Content-Type: application/json" \
  -d '{
    "file_name": "recording",
    "base64_audio": "<base64-wav-data>",
    "expected_text": "The cat sat on the mat."
  }'
```

Response includes:
- Transcribed text
- Expected vs actual phonemes
- Vowel accuracy scores
- Specific pronunciation feedback

## PowerApps Integration

The API is designed for PowerApps Desktop (PAD) integration via PowerShell bridges:

```powershell
# In PAD, use HTTP action or PowerShell script
$body = @{
    file_name = "recording"
    base64_audio = $audioBase64
    expected_text = "Hello, how are you?"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/assess" `
    -Method POST -Body $body -ContentType "application/json"

# Access feedback
$response.vowel_feedback
$response.overall_score
```

## English Vowels Reference

### Monophthongs
| IPA | Name | Example | Key Words |
|-----|------|---------|-----------|
| ɪ | short i | bit | ship, sit, hit |
| ɛ | short e | bet | bed, red, ten |
| æ | short a | bat | cat, sat, mat |
| ʌ | short u | but | bus, mud, cup |
| ʊ | short oo | book | put, hook, full |
| ə | schwa | about | today, hello |
| i | long ee | beat | sheep, eat, peas |
| u | long oo | boot | moon, cool, fool |
| ɔ | aw | bought | saw, law, caught |

### Diphthongs
| IPA | Name | Example | Key Words |
|-----|------|---------|-----------|
| eɪ | long a | bait | today, play, stay |
| oʊ | long o | boat | goat, rode, home |
| aɪ | long i | bite | kite, fly, sky |
| aʊ | ow | bout | how, cow, brown |
| ɔɪ | oy | boy | enjoy, toy |

## Service Configuration

### Ports

| Service | Internal | External | Purpose |
|---------|----------|----------|---------|
| Frontend | 80 | 3000 | React web UI |
| Pronunciation API | 8000 | 8000 | Main API gateway |
| Phoneme Service | 8001 | 8001 | wav2vec2 phoneme extraction |
| Whisper ASR | 9000 | 9002 | Speech-to-text |

### Health Check

```bash
# Check all services
curl -s http://localhost:8000/health | jq .
```

```json
{
  "status": "healthy",
  "whisper_status": "healthy",
  "phoneme_status": "healthy",
  "version": "1.0.0"
}
```

## Development

### Rebuild Single Service

```bash
docker compose up -d --build pronunciation-api
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f phoneme-service
```

### Stop Services

```bash
docker compose down
```

## Troubleshooting

### Services Not Starting

```bash
# Check status
docker compose ps

# View logs for failing service
docker compose logs pronunciation-api
```

### First Startup Slow

The phoneme-service downloads the wav2vec2 model (~1.2GB) on first startup. This can take 2-5 minutes depending on connection speed.

### Audio Issues in Browser

1. Ensure browser has microphone permissions
2. Check browser console (F12) for errors
3. Test microphone in system settings first
4. Try Chrome/Firefox (best WebAudio support)

### API Returns 500 Errors

```bash
# Check pronunciation-api logs
docker logs pronunciation-api --tail 50

# Check phoneme-service logs  
docker logs phoneme-service --tail 50
```

## Files Structure

```
pronunciation-system/
├── docker-compose.yml          # Service orchestration
├── README.md                   # This file
├── examples/
│   └── pronunciation_exercises_example.xlsx  # Example XLSX
├── pronunciation-api/          # Main API (FastAPI)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       └── services/
├── phoneme-service/            # Phoneme extraction (wav2vec2)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
└── frontend/                   # React web UI
    ├── Dockerfile
    ├── package.json
    └── src/
```

## License

MIT License - See LICENSE file for details.
