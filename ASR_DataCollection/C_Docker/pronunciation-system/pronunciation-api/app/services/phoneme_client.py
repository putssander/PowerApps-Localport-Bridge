"""
Phoneme Client

HTTP client for the Phoneme Service (wav2vec2 + WhisperX).
"""

import logging
from typing import Optional

import httpx

logger = logging.getLogger("pronunciation-api.phoneme_client")


class PhonemeClient:
    """HTTP client for Phoneme extraction and assessment service."""
    
    def __init__(self, base_url: str):
        """
        Initialize Phoneme client.
        
        Args:
            base_url: Base URL of Phoneme service (e.g., http://phoneme-service:8001)
        """
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=120.0)  # 2 minute timeout
        logger.info(f"Phoneme client initialized: {self.base_url}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def check_health(self) -> bool:
        """Check if Phoneme service is healthy and models are loaded."""
        try:
            response = await self.client.get(f"{self.base_url}/health", timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("models_loaded", False)
            return False
        except Exception as e:
            logger.warning(f"Phoneme health check failed: {e}")
            return False
    
    async def extract_phonemes(self, base64_audio: str) -> dict:
        """
        Extract IPA phonemes from audio.
        
        Args:
            base64_audio: Base64-encoded audio
            
        Returns:
            Dictionary with phonemes and phoneme_list
        """
        logger.debug("Extracting phonemes...")
        
        response = await self.client.post(
            f"{self.base_url}/phonemes",
            json={"base64_audio": base64_audio}
        )
        
        if response.status_code != 200:
            logger.error(f"Phoneme extraction error: {response.status_code} - {response.text}")
            raise Exception(f"Phoneme extraction failed: {response.text}")
        
        result = response.json()
        logger.debug(f"Extracted phonemes: {result.get('phonemes', '')[:100]}...")
        
        return result
    
    async def assess(
        self,
        base64_audio: str,
        expected_text: str,
        expected_phonemes: Optional[str] = None,
        focus_vowels: Optional[list[str]] = None
    ) -> dict:
        """
        Full pronunciation assessment.
        
        Args:
            base64_audio: Base64-encoded audio
            expected_text: Expected text/sentence
            expected_phonemes: Optional expected IPA phonemes
            focus_vowels: Optional list of vowels to focus on
            
        Returns:
            Assessment dictionary with scores and feedback
        """
        logger.debug(f"Assessing pronunciation for: '{expected_text[:50]}...'")
        
        payload = {
            "base64_audio": base64_audio,
            "expected_text": expected_text
        }
        
        if expected_phonemes:
            payload["expected_phonemes"] = expected_phonemes
        
        if focus_vowels:
            payload["focus_vowels"] = focus_vowels
        
        response = await self.client.post(
            f"{self.base_url}/assess",
            json=payload
        )
        
        if response.status_code != 200:
            logger.error(f"Assessment error: {response.status_code} - {response.text}")
            raise Exception(f"Pronunciation assessment failed: {response.text}")
        
        result = response.json()
        logger.debug(f"Assessment score: {result.get('overall_score', 0):.1%}")
        
        return result
