"""
Phoneme Extractor Service

Uses facebook/wav2vec2-lv-60-espeak-cv-ft to extract IPA phonemes from audio.
"""

import base64
import io
import logging
import subprocess
import tempfile
from typing import Optional

import numpy as np
import torch
import torchaudio
import soundfile as sf
from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC

logger = logging.getLogger("phoneme-service.extractor")

# Target sample rate for wav2vec2
TARGET_SAMPLE_RATE = 16000


class PhonemeExtractor:
    """
    Extracts IPA phonemes from audio using wav2vec2.
    
    Model: facebook/wav2vec2-lv-60-espeak-cv-ft
    - Fine-tuned on CommonVoice for multilingual phoneme recognition
    - Outputs espeak-based IPA phonemes
    """
    
    def __init__(self, device: str = "cpu"):
        """
        Initialize the phoneme extractor.
        
        Args:
            device: 'cpu' or 'cuda' for GPU acceleration
        """
        self.device = device if device == "cuda" and torch.cuda.is_available() else "cpu"
        self.model_name = "facebook/wav2vec2-lv-60-espeak-cv-ft"
        
        logger.info(f"Loading {self.model_name} on {self.device}...")
        
        self.processor = Wav2Vec2Processor.from_pretrained(self.model_name)
        self.model = Wav2Vec2ForCTC.from_pretrained(self.model_name).to(self.device)
        self.model.eval()
        
        logger.info("Phoneme extractor initialized successfully")
    
    def _decode_base64_audio(self, base64_audio: str) -> tuple[torch.Tensor, int]:
        """
        Decode base64 audio to torch tensor.
        
        Handles various formats (webm, ogg, mp3, wav) by using ffmpeg to convert
        to WAV format that soundfile can read.
        
        Args:
            base64_audio: Base64-encoded audio (any format ffmpeg supports)
            
        Returns:
            Tuple of (waveform tensor, sample_rate)
        """
        # Clean base64 string (remove whitespace, data URI prefix if present)
        clean_b64 = base64_audio.strip()
        if clean_b64.startswith("data:"):
            clean_b64 = clean_b64.split(",", 1)[1]
        
        # Decode to bytes
        audio_bytes = base64.b64decode(clean_b64)
        
        # Try direct loading with soundfile first (works for WAV, FLAC, OGG)
        try:
            audio_buffer = io.BytesIO(audio_bytes)
            data, sample_rate = sf.read(audio_buffer)
            logger.debug(f"Loaded audio directly: {sample_rate}Hz, {len(data)} samples")
        except Exception as e:
            logger.debug(f"Direct load failed ({e}), using ffmpeg conversion")
            # Use ffmpeg to convert to WAV format
            data, sample_rate = self._convert_with_ffmpeg(audio_bytes)
        
        # Convert to torch tensor
        # soundfile returns (samples, channels) for stereo, (samples,) for mono
        if len(data.shape) == 1:
            waveform = torch.tensor(data, dtype=torch.float32).unsqueeze(0)
        else:
            waveform = torch.tensor(data.T, dtype=torch.float32)
        
        return waveform, sample_rate
    
    def _convert_with_ffmpeg(self, audio_bytes: bytes) -> tuple[np.ndarray, int]:
        """
        Convert audio bytes to WAV format using ffmpeg.
        
        Args:
            audio_bytes: Raw audio bytes in any format
            
        Returns:
            Tuple of (audio data as numpy array, sample_rate)
        """
        with tempfile.NamedTemporaryFile(suffix=".input", delete=False) as input_file:
            input_path = input_file.name
            input_file.write(audio_bytes)
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as output_file:
            output_path = output_file.name
        
        try:
            # Convert to 16kHz mono WAV using ffmpeg
            cmd = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-ar", str(TARGET_SAMPLE_RATE),
                "-ac", "1",
                "-f", "wav",
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"ffmpeg error: {result.stderr.decode()}")
                raise RuntimeError(f"ffmpeg conversion failed: {result.stderr.decode()}")
            
            # Read the converted WAV file
            data, sample_rate = sf.read(output_path)
            logger.debug(f"Converted audio: {sample_rate}Hz, {len(data)} samples")
            
            return data, sample_rate
            
        finally:
            # Clean up temp files
            import os
            try:
                os.unlink(input_path)
            except:
                pass
            try:
                os.unlink(output_path)
            except:
                pass
    
    def _preprocess_audio(self, waveform: torch.Tensor, sample_rate: int) -> torch.Tensor:
        """
        Preprocess audio for wav2vec2.
        
        - Convert to mono if stereo
        - Resample to 16kHz
        - Normalize
        """
        # Convert to mono if needed
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
        
        # Resample if needed
        if sample_rate != TARGET_SAMPLE_RATE:
            resampler = torchaudio.transforms.Resample(sample_rate, TARGET_SAMPLE_RATE)
            waveform = resampler(waveform)
        
        # Squeeze to 1D
        waveform = waveform.squeeze()
        
        return waveform
    
    async def extract_from_base64(self, base64_audio: str) -> dict:
        """
        Extract phonemes from base64-encoded audio.
        
        Args:
            base64_audio: Base64-encoded WAV audio
            
        Returns:
            Dictionary with:
            - phonemes: Space-separated IPA phoneme string
            - phoneme_list: List of individual phonemes
        """
        # Decode and preprocess
        waveform, sample_rate = self._decode_base64_audio(base64_audio)
        waveform = self._preprocess_audio(waveform, sample_rate)
        
        # Process through model
        inputs = self.processor(
            waveform.numpy(),
            sampling_rate=TARGET_SAMPLE_RATE,
            return_tensors="pt",
            padding=True
        )
        
        input_values = inputs.input_values.to(self.device)
        
        with torch.no_grad():
            logits = self.model(input_values).logits
        
        # Decode predictions
        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = self.processor.batch_decode(predicted_ids)
        
        # Parse phonemes
        phoneme_string = transcription[0] if transcription else ""
        phoneme_list = [p for p in phoneme_string.split() if p]
        
        logger.debug(f"Extracted {len(phoneme_list)} phonemes: {phoneme_string[:100]}...")
        
        return {
            "phonemes": phoneme_string,
            "phoneme_list": phoneme_list
        }
    
    async def extract_from_file(self, file_path: str) -> dict:
        """
        Extract phonemes from an audio file.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dictionary with phonemes and phoneme_list
        """
        waveform, sample_rate = torchaudio.load(file_path)
        waveform = self._preprocess_audio(waveform, sample_rate)
        
        inputs = self.processor(
            waveform.numpy(),
            sampling_rate=TARGET_SAMPLE_RATE,
            return_tensors="pt",
            padding=True
        )
        
        input_values = inputs.input_values.to(self.device)
        
        with torch.no_grad():
            logits = self.model(input_values).logits
        
        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = self.processor.batch_decode(predicted_ids)
        
        phoneme_string = transcription[0] if transcription else ""
        phoneme_list = [p for p in phoneme_string.split() if p]
        
        return {
            "phonemes": phoneme_string,
            "phoneme_list": phoneme_list
        }
