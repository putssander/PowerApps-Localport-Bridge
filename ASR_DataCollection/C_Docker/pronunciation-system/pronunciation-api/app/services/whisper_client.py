"""
Whisper Client

HTTP client for the Whisper ASR container.
"""

import base64
import logging
import tempfile
from typing import Optional

import httpx

logger = logging.getLogger("pronunciation-api.whisper_client")


class WhisperClient:
    """HTTP client for Whisper ASR service."""
    
    def __init__(self, base_url: str):
        """
        Initialize Whisper client.
        
        Args:
            base_url: Base URL of Whisper service (e.g., http://whisper-asr:9000)
        """
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=300.0)  # 5 minute timeout for long audio
        logger.info(f"Whisper client initialized: {self.base_url}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def check_health(self) -> bool:
        """Check if Whisper service is healthy."""
        try:
            # Check the OpenAPI docs endpoint which returns 200
            response = await self.client.get(f"{self.base_url}/openapi.json", timeout=10.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Whisper health check failed: {e}")
            return False
    
    async def transcribe(
        self,
        base64_audio: str,
        language: str = "en",
        task: str = "transcribe",
        output_format: str = "txt"
    ) -> str:
        """
        Transcribe audio using Whisper.
        
        Args:
            base64_audio: Base64-encoded audio (WAV format)
            language: Language code
            task: 'transcribe' or 'translate'
            output_format: Output format (txt, srt, vtt, json)
            
        Returns:
            Transcription text
        """
        logger.debug(f"Transcribing audio (format={output_format}, lang={language})")
        
        # Clean base64 string
        clean_b64 = base64_audio.strip()
        if clean_b64.startswith("data:"):
            clean_b64 = clean_b64.split(",", 1)[1]
        
        # Decode to bytes
        audio_bytes = base64.b64decode(clean_b64)
        
        # Prepare multipart form data
        files = {
            "audio_file": ("audio.wav", audio_bytes, "audio/wav")
        }
        
        params = {
            "encode": "true",
            "task": task,
            "language": language,
            "output": output_format
        }
        
        # Call Whisper API
        response = await self.client.post(
            f"{self.base_url}/asr",
            files=files,
            params=params
        )
        
        if response.status_code != 200:
            logger.error(f"Whisper error: {response.status_code} - {response.text}")
            raise Exception(f"Whisper transcription failed: {response.text}")
        
        transcription = response.text.strip()
        logger.debug(f"Transcription: {transcription[:100]}...")
        
        return transcription
