"""
Pronunciation API - Main Orchestration Service

Coordinates between Whisper ASR, Phoneme Service, and provides
PowerApps-compatible endpoints for the pronunciation teaching system.
"""

import os
import time
import logging
import uuid
import json
from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from app.services.exercise_service import ExerciseService
from app.services.whisper_client import WhisperClient
from app.services.phoneme_client import PhonemeClient

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("pronunciation-api")

# Service URLs from environment
WHISPER_URL = os.getenv("WHISPER_URL", "http://localhost:9001")
PHONEME_URL = os.getenv("PHONEME_URL", "http://localhost:8001")
EXERCISES_DIR = Path(os.getenv("EXERCISES_DIR", "./exercises"))

# Global service instances
whisper_client: Optional[WhisperClient] = None
phoneme_client: Optional[PhonemeClient] = None
exercise_service: Optional[ExerciseService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize service clients on startup."""
    global whisper_client, phoneme_client, exercise_service
    
    logger.info("=" * 60)
    logger.info("PRONUNCIATION API STARTING")
    logger.info(f"Whisper URL: {WHISPER_URL}")
    logger.info(f"Phoneme URL: {PHONEME_URL}")
    logger.info(f"Exercises dir: {EXERCISES_DIR}")
    logger.info("=" * 60)
    
    # Initialize clients
    whisper_client = WhisperClient(WHISPER_URL)
    phoneme_client = PhonemeClient(PHONEME_URL)
    exercise_service = ExerciseService(EXERCISES_DIR)
    
    # Ensure exercises directory exists
    EXERCISES_DIR.mkdir(parents=True, exist_ok=True)
    
    logger.info("Pronunciation API ready")
    
    yield
    
    # Cleanup
    logger.info("Shutting down pronunciation API...")
    await whisper_client.close()
    await phoneme_client.close()


app = FastAPI(
    title="Pronunciation Teaching API",
    description="Backend API for English pronunciation teaching system with vowel-specific feedback",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Request/Response Models - PowerApps Compatible
# =============================================================================

class TranscribeRequest(BaseModel):
    """PowerApps-compatible transcription request."""
    file_name: str
    format: Optional[str] = None
    base64_audio: str


class TranscribeResponse(BaseModel):
    """PowerApps-compatible transcription response with optional assessment."""
    file_name: str
    transcription: str
    phoneme_assessment: Optional[dict] = None


class AssessRequest(BaseModel):
    """Full assessment request."""
    file_name: str
    base64_audio: str
    expected_text: str
    expected_phonemes: Optional[str] = None
    focus_vowels: Optional[list[str]] = None


class ExerciseUploadResponse(BaseModel):
    """Response after uploading exercise XLSX."""
    exercise_id: str
    sentence_count: int
    auto_generated_phonemes: int
    sentences: list[dict]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    whisper_status: str
    phoneme_status: str
    version: str


# =============================================================================
# Health & Info Endpoints
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check with downstream service status."""
    whisper_ok = await whisper_client.check_health()
    phoneme_ok = await phoneme_client.check_health()
    
    return HealthResponse(
        status="healthy" if (whisper_ok and phoneme_ok) else "degraded",
        whisper_status="healthy" if whisper_ok else "unhealthy",
        phoneme_status="healthy" if phoneme_ok else "unhealthy",
        version="1.0.0"
    )


@app.get("/")
async def root():
    """API info endpoint."""
    return {
        "service": "pronunciation-api",
        "version": "1.0.0",
        "endpoints": {
            "transcription": "/transcribe (POST) - PowerApps compatible",
            "assessment": "/assess (POST) - Full pronunciation assessment",
            "exercises": "/exercises (GET, POST) - XLSX exercise management",
            "streaming": "/stream (WebSocket) - Real-time feedback"
        }
    }


# =============================================================================
# PowerApps-Compatible Transcription Endpoint
# =============================================================================

@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(request: TranscribeRequest):
    """
    Transcribe audio - PowerApps compatible.
    
    This endpoint maintains backward compatibility with existing PAD bridges.
    Returns transcription and optionally phoneme assessment.
    
    Request format (from PAD):
        {
            "file_name": "audio_001",
            "format": "formattedDu",  // optional
            "base64_audio": "..."
        }
    
    Response format:
        {
            "file_name": "audio_001",
            "transcription": "Hello world",
            "phoneme_assessment": {...}  // optional, for new integrations
        }
    """
    logger.info(f"Transcription request: {request.file_name}")
    start_time = time.time()
    
    try:
        # Call Whisper for transcription
        transcription = await whisper_client.transcribe(
            request.base64_audio,
            output_format=request.format or "txt"
        )
        
        logger.info(f"Transcription completed in {time.time() - start_time:.2f}s")
        
        return TranscribeResponse(
            file_name=request.file_name,
            transcription=transcription,
            phoneme_assessment=None  # Basic transcription, no assessment
        )
        
    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


# =============================================================================
# Full Pronunciation Assessment Endpoint
# =============================================================================

@app.post("/assess")
async def assess_pronunciation(request: AssessRequest):
    """
    Full pronunciation assessment with vowel feedback.
    
    Pipeline:
    1. Transcribe with Whisper
    2. Extract phonemes and align with phoneme-service
    3. Compare against expected pronunciation
    4. Return detailed vowel-specific feedback
    """
    logger.info(f"Assessment request: {request.file_name} | Expected: '{request.expected_text[:50]}...'")
    start_time = time.time()
    
    try:
        # Step 1: Get transcription from Whisper
        logger.debug("Step 1: Whisper transcription...")
        transcription = await whisper_client.transcribe(request.base64_audio)
        
        # Step 2: Get phoneme assessment from phoneme-service
        logger.debug("Step 2: Phoneme assessment...")
        assessment = await phoneme_client.assess(
            base64_audio=request.base64_audio,
            expected_text=request.expected_text,
            expected_phonemes=request.expected_phonemes,
            focus_vowels=request.focus_vowels
        )
        
        processing_time = time.time() - start_time
        logger.info(
            f"Assessment completed in {processing_time:.2f}s | "
            f"Score: {assessment.get('overall_score', 0):.1%}"
        )
        
        # Return PowerApps-compatible response with extended assessment
        return {
            "file_name": request.file_name,
            "transcription": transcription,
            "phoneme_assessment": assessment,
            "processing_time_ms": int(processing_time * 1000)
        }
        
    except Exception as e:
        logger.error(f"Assessment failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")


# =============================================================================
# Exercise Management Endpoints
# =============================================================================

@app.get("/exercises/example/download")
async def download_example():
    """Download the example XLSX exercise file."""
    example_path = Path("/app/exercises/pronunciation_exercises_example.xlsx")
    if not example_path.exists():
        raise HTTPException(status_code=404, detail="Example file not found")
    
    return FileResponse(
        path=example_path,
        filename="pronunciation_exercises_example.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.get("/exercises")
async def list_exercises():
    """List all available exercises."""
    exercises = exercise_service.list_exercises()
    return {"exercises": exercises}


@app.get("/exercises/{exercise_id}")
async def get_exercise(exercise_id: str):
    """Get a specific exercise by ID."""
    exercise = exercise_service.get_exercise(exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return exercise


@app.post("/exercises/upload", response_model=ExerciseUploadResponse)
async def upload_exercise(file: UploadFile = File(...)):
    """
    Upload an XLSX exercise file.
    
    Expected format:
    - Column A: Sentence text
    - Column B: Expected IPA phonemes (optional, auto-generated if empty)
    - Column C: Focus vowels (optional)
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="File must be .xlsx or .xls")
    
    logger.info(f"Uploading exercise file: {file.filename}")
    
    try:
        contents = await file.read()
        result = exercise_service.import_xlsx(contents, file.filename)
        
        logger.info(
            f"Exercise imported: {result['exercise_id']} | "
            f"{result['sentence_count']} sentences | "
            f"{result['auto_generated_phonemes']} auto-generated"
        )
        
        return ExerciseUploadResponse(**result)
        
    except Exception as e:
        logger.error(f"Exercise upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to parse exercise file: {str(e)}")


@app.delete("/exercises/{exercise_id}")
async def delete_exercise(exercise_id: str):
    """Delete an exercise."""
    success = exercise_service.delete_exercise(exercise_id)
    if not success:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return {"status": "deleted", "exercise_id": exercise_id}


# =============================================================================
# WebSocket Streaming Endpoint
# =============================================================================

@app.websocket("/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time pronunciation feedback.
    
    Protocol:
    1. Client sends: {"type": "start", "expected_text": "..."}
    2. Client sends audio chunks: {"type": "audio", "data": "base64..."}
    3. Server responds per-word: {"type": "word_result", "word": "...", "score": 0.85}
    4. Server sends final: {"type": "complete", "overall_score": 0.82}
    """
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    expected_text = ""
    audio_buffer = []
    
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "start":
                expected_text = data.get("expected_text", "")
                audio_buffer = []
                await websocket.send_json({
                    "type": "ready",
                    "message": f"Ready to assess: '{expected_text[:50]}...'"
                })
                
            elif msg_type == "audio":
                # Accumulate audio chunk
                audio_buffer.append(data.get("data", ""))
                
            elif msg_type == "end":
                # Process complete audio
                if not expected_text:
                    await websocket.send_json({
                        "type": "error",
                        "message": "No expected text set. Send 'start' message first."
                    })
                    continue
                
                # Combine audio chunks
                full_audio = "".join(audio_buffer)
                
                await websocket.send_json({
                    "type": "processing",
                    "message": "Analyzing pronunciation..."
                })
                
                # Get assessment
                try:
                    assessment = await phoneme_client.assess(
                        base64_audio=full_audio,
                        expected_text=expected_text
                    )
                    
                    # Send word-by-word results
                    for word_detail in assessment.get("word_details", []):
                        await websocket.send_json({
                            "type": "word_result",
                            "word": word_detail.get("word"),
                            "expected_vowels": word_detail.get("expected_vowels"),
                            "start_ms": word_detail.get("start_ms"),
                            "end_ms": word_detail.get("end_ms"),
                            "confidence": word_detail.get("confidence")
                        })
                    
                    # Send complete summary
                    await websocket.send_json({
                        "type": "complete",
                        "overall_score": assessment.get("overall_score"),
                        "vowel_score": assessment.get("vowel_score"),
                        "vowel_errors": assessment.get("vowel_errors"),
                        "focus_areas": assessment.get("focus_areas")
                    })
                    
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                
                # Reset for next assessment
                audio_buffer = []
                
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
