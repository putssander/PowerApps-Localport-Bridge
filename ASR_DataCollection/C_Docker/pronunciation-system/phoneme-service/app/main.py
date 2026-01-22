"""
Phoneme Service - Main FastAPI Application

Provides phoneme extraction using wav2vec2 and word-level alignment using WhisperX.
Models are preloaded at startup for fast inference.
"""

import os
import time
import logging
from contextlib import asynccontextmanager
from typing import Optional

import torch
import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.phoneme_extractor import PhonemeExtractor
from app.services.alignment_service import AlignmentService
from app.services.vowel_assessor import VowelAssessor

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("phoneme-service")

# Global service instances
phoneme_extractor: Optional[PhonemeExtractor] = None
alignment_service: Optional[AlignmentService] = None
vowel_assessor: Optional[VowelAssessor] = None
models_loaded: bool = False
model_load_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models at startup, cleanup on shutdown."""
    global phoneme_extractor, alignment_service, vowel_assessor, models_loaded, model_load_time
    
    device = os.getenv("DEVICE", "cpu")
    logger.info("=" * 60)
    logger.info("PHONEME SERVICE STARTING")
    logger.info(f"Device: {device}")
    logger.info(f"PyTorch version: {torch.__version__}")
    if device == "cuda":
        logger.info(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
    logger.info("=" * 60)
    
    start_time = time.time()
    
    try:
        # Load phoneme extraction model (wav2vec2)
        logger.info("Loading wav2vec2 phoneme model (facebook/wav2vec2-lv-60-espeak-cv-ft)...")
        phoneme_start = time.time()
        phoneme_extractor = PhonemeExtractor(device=device)
        logger.info(f"✓ Phoneme model loaded in {time.time() - phoneme_start:.2f}s")
        
        # Load WhisperX alignment model
        logger.info("Loading WhisperX alignment model...")
        align_start = time.time()
        alignment_service = AlignmentService(device=device)
        logger.info(f"✓ WhisperX alignment ready in {time.time() - align_start:.2f}s")
        
        # Initialize vowel assessor
        logger.info("Initializing vowel assessment service...")
        vowel_assessor = VowelAssessor()
        logger.info("✓ Vowel assessor ready")
        
        model_load_time = time.time() - start_time
        models_loaded = True
        
        logger.info("=" * 60)
        logger.info(f"ALL MODELS LOADED SUCCESSFULLY in {model_load_time:.2f}s")
        logger.info("Service ready to accept requests")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Failed to load models: {e}", exc_info=True)
        raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down phoneme service...")
    phoneme_extractor = None
    alignment_service = None
    vowel_assessor = None


app = FastAPI(
    title="Phoneme Service",
    description="Phoneme extraction and pronunciation assessment using wav2vec2 and WhisperX",
    version="1.0.0",
    lifespan=lifespan
)


# =============================================================================
# Request/Response Models
# =============================================================================

class PhonemeRequest(BaseModel):
    """Request for phoneme extraction from base64 audio."""
    base64_audio: str
    expected_text: Optional[str] = None
    expected_phonemes: Optional[str] = None


class PhonemeResponse(BaseModel):
    """Response with extracted phonemes and assessment."""
    phonemes: str
    phoneme_list: list[str]
    word_alignments: Optional[list[dict]] = None


class AssessmentRequest(BaseModel):
    """Request for full pronunciation assessment."""
    base64_audio: str
    expected_text: str
    expected_phonemes: Optional[str] = None
    focus_vowels: Optional[list[str]] = None


class AssessmentResponse(BaseModel):
    """Full pronunciation assessment response."""
    transcription: str
    phonemes: str
    overall_score: float
    vowel_score: float
    vowel_errors: list[dict]
    focus_areas: list[str]
    word_details: list[dict]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    models_loaded: bool
    model_load_time_seconds: float
    device: str


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with model status."""
    return HealthResponse(
        status="healthy" if models_loaded else "loading",
        models_loaded=models_loaded,
        model_load_time_seconds=round(model_load_time, 2),
        device=os.getenv("DEVICE", "cpu")
    )


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "phoneme-service",
        "version": "1.0.0",
        "status": "ready" if models_loaded else "loading",
        "endpoints": ["/health", "/phonemes", "/assess", "/align"]
    }


@app.post("/phonemes", response_model=PhonemeResponse)
async def extract_phonemes(request: PhonemeRequest):
    """
    Extract IPA phonemes from audio.
    
    Uses facebook/wav2vec2-lv-60-espeak-cv-ft to convert audio to IPA phoneme sequence.
    """
    if not models_loaded:
        raise HTTPException(status_code=503, detail="Models still loading, please wait")
    
    logger.info("Processing phoneme extraction request...")
    start_time = time.time()
    
    try:
        # Extract phonemes
        result = await phoneme_extractor.extract_from_base64(request.base64_audio)
        
        logger.info(f"Phoneme extraction completed in {time.time() - start_time:.2f}s")
        logger.debug(f"Extracted phonemes: {result['phonemes']}")
        
        return PhonemeResponse(
            phonemes=result["phonemes"],
            phoneme_list=result["phoneme_list"],
            word_alignments=result.get("word_alignments")
        )
        
    except Exception as e:
        logger.error(f"Phoneme extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/assess", response_model=AssessmentResponse)
async def assess_pronunciation(request: AssessmentRequest):
    """
    Full pronunciation assessment with vowel-specific feedback.
    
    Pipeline:
    1. Extract phonemes using wav2vec2
    2. Align words using WhisperX
    3. Compare against expected pronunciation
    4. Generate vowel-specific feedback with timestamps
    """
    if not models_loaded:
        raise HTTPException(status_code=503, detail="Models still loading, please wait")
    
    logger.info(f"Processing assessment request for: '{request.expected_text[:50]}...'")
    start_time = time.time()
    
    try:
        # Step 1: Extract actual phonemes from audio
        logger.debug("Step 1: Extracting phonemes...")
        phoneme_result = await phoneme_extractor.extract_from_base64(request.base64_audio)
        
        # Step 2: Get word-level alignments
        logger.debug("Step 2: Aligning words...")
        alignment_result = await alignment_service.align_from_base64(
            request.base64_audio,
            request.expected_text
        )
        
        # Step 3: Assess pronunciation
        logger.debug("Step 3: Assessing vowels...")
        assessment = vowel_assessor.assess(
            expected_text=request.expected_text,
            expected_phonemes=request.expected_phonemes,
            actual_phonemes=phoneme_result["phonemes"],
            actual_phoneme_list=phoneme_result["phoneme_list"],
            word_alignments=alignment_result.get("word_segments", []),
            focus_vowels=request.focus_vowels
        )
        
        processing_time = time.time() - start_time
        logger.info(f"Assessment completed in {processing_time:.2f}s | Score: {assessment['overall_score']:.1%}")
        
        return AssessmentResponse(
            transcription=alignment_result.get("text", ""),
            phonemes=phoneme_result["phonemes"],
            overall_score=assessment["overall_score"],
            vowel_score=assessment["vowel_score"],
            vowel_errors=assessment["vowel_errors"],
            focus_areas=assessment["focus_areas"],
            word_details=assessment["word_details"]
        )
        
    except Exception as e:
        logger.error(f"Assessment failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/align")
async def align_audio(file: UploadFile = File(...), text: str = ""):
    """
    Align audio with text using WhisperX.
    
    Returns word-level timestamps for visualization.
    """
    if not models_loaded:
        raise HTTPException(status_code=503, detail="Models still loading, please wait")
    
    logger.info(f"Processing alignment request...")
    
    try:
        audio_bytes = await file.read()
        result = await alignment_service.align_from_bytes(audio_bytes, text)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Alignment failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
