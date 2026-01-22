"""
Alignment Service - Direct wav2vec2 Phoneme Extraction

Uses wav2vec2 model directly for phoneme-level extraction and timing.
No WhisperX dependency - cleaner and more reliable.

The key model: facebook/wav2vec2-lv-60-espeak-cv-ft
- Outputs IPA phonemes directly from audio
- Provides frame-level probabilities for timing
"""

import base64
import io
import logging
import subprocess
import tempfile
import os
from typing import Optional, List, Dict, Any

import numpy as np
import torch
import librosa
import soundfile as sf
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

logger = logging.getLogger("phoneme-service.alignment")


class AlignmentService:
    """
    Provides phoneme-level alignment using wav2vec2 directly.
    
    Extracts IPA phonemes with timestamps for pronunciation feedback.
    """
    
    def __init__(self, device: str = "cpu"):
        """
        Initialize the alignment service with wav2vec2 phoneme model.
        
        Args:
            device: 'cpu' or 'cuda'
        """
        self.device = device if device == "cuda" and torch.cuda.is_available() else "cpu"
        self.sample_rate = 16000  # wav2vec2 expects 16kHz
        self.frame_duration = 0.02  # 20ms per frame
        
        logger.info(f"Loading wav2vec2 phoneme model on {self.device}...")
        
        # Load the phoneme-specific wav2vec2 model
        model_name = "facebook/wav2vec2-lv-60-espeak-cv-ft"
        self.processor = Wav2Vec2Processor.from_pretrained(model_name)
        self.model = Wav2Vec2ForCTC.from_pretrained(model_name).to(self.device)
        self.model.eval()
        
        logger.info("wav2vec2 phoneme alignment service initialized")
    
    def _convert_with_ffmpeg(self, audio_bytes: bytes) -> np.ndarray:
        """
        Convert audio bytes to 16kHz mono WAV using ffmpeg.
        """
        with tempfile.NamedTemporaryFile(suffix=".input", delete=False) as input_file:
            input_path = input_file.name
            input_file.write(audio_bytes)
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as output_file:
            output_path = output_file.name
        
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-ar", str(self.sample_rate),
                "-ac", "1",
                "-f", "wav",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg conversion failed: {result.stderr.decode()}")
            
            audio, sr = sf.read(output_path)
            return audio.astype(np.float32)
            
        finally:
            try:
                os.unlink(input_path)
            except:
                pass
            try:
                os.unlink(output_path)
            except:
                pass
    
    def _decode_audio(self, base64_audio: str) -> np.ndarray:
        """
        Decode base64 audio to numpy array at 16kHz.
        Handles various formats (webm, ogg, mp3, wav) via ffmpeg.
        """
        clean_b64 = base64_audio.strip()
        if clean_b64.startswith("data:"):
            clean_b64 = clean_b64.split(",", 1)[1]
        
        audio_bytes = base64.b64decode(clean_b64)
        
        # Try direct loading first (works for WAV, FLAC, OGG)
        try:
            audio, sr = sf.read(io.BytesIO(audio_bytes))
            
            # Convert to mono if stereo
            if len(audio.shape) > 1:
                audio = audio.mean(axis=1)
            
            # Resample to 16kHz if needed
            if sr != self.sample_rate:
                audio = librosa.resample(audio, orig_sr=sr, target_sr=self.sample_rate)
            
            return audio.astype(np.float32)
            
        except Exception as e:
            logger.debug(f"Direct load failed ({e}), using ffmpeg")
            return self._convert_with_ffmpeg(audio_bytes)
    
    def extract_phonemes_with_timing(self, audio: np.ndarray) -> List[Dict[str, Any]]:
        """
        Extract phonemes from audio with timestamps.
        
        Returns list of phoneme segments with start/end times.
        """
        # Process audio
        inputs = self.processor(
            audio, 
            sampling_rate=self.sample_rate, 
            return_tensors="pt",
            padding=True
        )
        
        with torch.no_grad():
            input_values = inputs.input_values.to(self.device)
            logits = self.model(input_values).logits
        
        # Get predicted phoneme IDs
        predicted_ids = torch.argmax(logits, dim=-1)
        
        # Get frame-level predictions for timing
        probs = torch.softmax(logits, dim=-1)
        predicted_probs, _ = torch.max(probs, dim=-1)
        
        # Calculate timestamps for each frame
        num_frames = logits.shape[1]
        audio_duration = len(audio) / self.sample_rate
        frame_duration = audio_duration / num_frames
        
        # Group consecutive frames with same phoneme
        phoneme_segments = []
        current_phoneme = None
        segment_start = 0
        segment_probs = []
        
        ids = predicted_ids[0].cpu().numpy()
        probs_np = predicted_probs[0].cpu().numpy()
        
        for i, (pid, prob) in enumerate(zip(ids, probs_np)):
            phoneme = self.processor.decode([pid]).strip()
            
            if phoneme != current_phoneme:
                # Save previous segment
                if current_phoneme and current_phoneme not in ['', '<pad>', '|']:
                    phoneme_segments.append({
                        "phoneme": current_phoneme,
                        "start": round(segment_start, 3),
                        "end": round(i * frame_duration, 3),
                        "confidence": round(float(np.mean(segment_probs)), 3)
                    })
                
                # Start new segment
                current_phoneme = phoneme
                segment_start = i * frame_duration
                segment_probs = [prob]
            else:
                segment_probs.append(prob)
        
        # Don't forget last segment
        if current_phoneme and current_phoneme not in ['', '<pad>', '|']:
            phoneme_segments.append({
                "phoneme": current_phoneme,
                "start": round(segment_start, 3),
                "end": round(audio_duration, 3),
                "confidence": round(float(np.mean(segment_probs)), 3)
            })
        
        return phoneme_segments
    
    async def align_from_base64(
        self,
        base64_audio: str,
        expected_text: Optional[str] = None
    ) -> dict:
        """
        Extract phonemes from audio with timestamps.
        
        Args:
            base64_audio: Base64-encoded WAV audio
            expected_text: Expected text (for comparison)
            
        Returns:
            Dictionary with phoneme segments and timing
        """
        # Decode audio
        audio = self._decode_audio(base64_audio)
        audio_duration = len(audio) / self.sample_rate
        
        # Extract phonemes with timing
        phoneme_segments = self.extract_phonemes_with_timing(audio)
        
        # Build full phoneme transcription
        phoneme_text = " ".join([s["phoneme"] for s in phoneme_segments])
        
        logger.debug(f"Extracted {len(phoneme_segments)} phoneme segments")
        
        result = {
            "phonemes": phoneme_text,
            "phoneme_segments": phoneme_segments,
            "duration": round(audio_duration, 3),
            "num_phonemes": len(phoneme_segments)
        }
        
        if expected_text:
            result["expected_text"] = expected_text
        
        return result
    
    async def align_from_bytes(
        self,
        audio_bytes: bytes,
        expected_text: Optional[str] = None
    ) -> dict:
        """
        Extract phonemes from audio bytes.
        """
        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
        return await self.align_from_base64(b64_audio, expected_text)
    
    async def get_phoneme_alignment(
        self,
        base64_audio: str,
        expected_phonemes: List[str]
    ) -> Dict[str, Any]:
        """
        Align audio against expected phonemes and score each one.
        
        Args:
            base64_audio: Base64-encoded audio
            expected_phonemes: List of expected IPA phonemes
            
        Returns:
            Alignment results with per-phoneme scores
        """
        result = await self.align_from_base64(base64_audio)
        detected_phonemes = [s["phoneme"] for s in result["phoneme_segments"]]
        
        # Simple alignment scoring
        alignment_scores = []
        for i, expected in enumerate(expected_phonemes):
            if i < len(detected_phonemes):
                detected = detected_phonemes[i]
                match = 1.0 if detected == expected else 0.0
                # Partial credit for similar phonemes
                if match == 0.0 and self._phonemes_similar(expected, detected):
                    match = 0.5
                alignment_scores.append({
                    "expected": expected,
                    "detected": detected,
                    "score": match,
                    "timing": result["phoneme_segments"][i] if i < len(result["phoneme_segments"]) else None
                })
            else:
                alignment_scores.append({
                    "expected": expected,
                    "detected": None,
                    "score": 0.0,
                    "timing": None
                })
        
        return {
            "alignment": alignment_scores,
            "overall_score": np.mean([s["score"] for s in alignment_scores]) if alignment_scores else 0.0,
            "detected_phonemes": detected_phonemes,
            "expected_phonemes": expected_phonemes
        }
    
    def _phonemes_similar(self, p1: str, p2: str) -> bool:
        """Check if two phonemes are acoustically similar."""
        # Group similar vowels
        vowel_groups = [
            {'i', 'ɪ', 'iː'},
            {'e', 'ɛ', 'eɪ'},
            {'æ', 'a', 'ɑ'},
            {'ɔ', 'o', 'oʊ', 'ɒ'},
            {'u', 'ʊ', 'uː'},
            {'ə', 'ʌ', 'ɜ'}
        ]
        
        for group in vowel_groups:
            if p1 in group and p2 in group:
                return True
        
        # Group similar consonants
        consonant_groups = [
            {'t', 'd'},
            {'p', 'b'},
            {'k', 'g'},
            {'f', 'v'},
            {'s', 'z'},
            {'θ', 'ð'},
            {'ʃ', 'ʒ'},
            {'tʃ', 'dʒ'}
        ]
        
        for group in consonant_groups:
            if p1 in group and p2 in group:
                return True
        
        return False
