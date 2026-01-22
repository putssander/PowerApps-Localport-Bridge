"""
Vowel Assessor Service

Compares expected and actual phonemes with focus on English vowels.
Provides per-vowel accuracy and identifies common substitution patterns.
"""

import logging
import re
from typing import Optional
from difflib import SequenceMatcher

from g2p_en import G2p

logger = logging.getLogger("phoneme-service.vowel_assessor")


# =============================================================================
# English Vowel Phoneme Definitions
# =============================================================================

# IPA vowels (from wav2vec2 espeak output)
IPA_VOWELS = {
    # Monophthongs (short)
    'ɪ': {'name': 'short i', 'example': 'bit', 'difficulty': 'high'},
    'ɛ': {'name': 'short e', 'example': 'bet', 'difficulty': 'medium'},
    'æ': {'name': 'short a', 'example': 'bat', 'difficulty': 'high'},
    'ɑ': {'name': 'short o', 'example': 'bot', 'difficulty': 'medium'},
    'ʌ': {'name': 'short u', 'example': 'but', 'difficulty': 'high'},
    'ʊ': {'name': 'short oo', 'example': 'book', 'difficulty': 'high'},
    'ə': {'name': 'schwa', 'example': 'about', 'difficulty': 'high'},
    
    # Monophthongs (long)
    'i': {'name': 'long ee', 'example': 'beat', 'difficulty': 'low'},
    'iː': {'name': 'long ee', 'example': 'beat', 'difficulty': 'low'},
    'u': {'name': 'long oo', 'example': 'boot', 'difficulty': 'low'},
    'uː': {'name': 'long oo', 'example': 'boot', 'difficulty': 'low'},
    'ɔ': {'name': 'aw', 'example': 'bought', 'difficulty': 'medium'},
    'ɔː': {'name': 'aw', 'example': 'bought', 'difficulty': 'medium'},
    'ɜ': {'name': 'ur', 'example': 'bird', 'difficulty': 'high'},
    'ɜː': {'name': 'ur', 'example': 'bird', 'difficulty': 'high'},
    'ɑː': {'name': 'ah', 'example': 'father', 'difficulty': 'medium'},
    
    # Diphthongs
    'eɪ': {'name': 'long a', 'example': 'bait', 'difficulty': 'medium'},
    'oʊ': {'name': 'long o', 'example': 'boat', 'difficulty': 'medium'},
    'aɪ': {'name': 'long i', 'example': 'bite', 'difficulty': 'medium'},
    'aʊ': {'name': 'ow', 'example': 'bout', 'difficulty': 'medium'},
    'ɔɪ': {'name': 'oy', 'example': 'boy', 'difficulty': 'low'},
    'ɪə': {'name': 'ear', 'example': 'beer', 'difficulty': 'high'},
    'eə': {'name': 'air', 'example': 'bear', 'difficulty': 'high'},
    'ʊə': {'name': 'oor', 'example': 'poor', 'difficulty': 'high'},
}

# ARPAbet vowels (from g2p-en / CMU dict)
ARPABET_VOWELS = {
    'AA': 'ɑ', 'AE': 'æ', 'AH': 'ʌ', 'AO': 'ɔ', 'AW': 'aʊ',
    'AY': 'aɪ', 'EH': 'ɛ', 'ER': 'ɜ', 'EY': 'eɪ', 'IH': 'ɪ',
    'IY': 'i', 'OW': 'oʊ', 'OY': 'ɔɪ', 'UH': 'ʊ', 'UW': 'u',
}

# Common vowel confusion pairs (L1 interference patterns)
COMMON_CONFUSIONS = [
    ('ɪ', 'i'),   # bit vs beat
    ('ɛ', 'eɪ'),  # bet vs bait
    ('æ', 'ɛ'),   # bat vs bet
    ('ʌ', 'ɑ'),   # but vs bot
    ('ʊ', 'u'),   # book vs boot
    ('ɔ', 'oʊ'),  # caught vs coat
]


class VowelAssessor:
    """
    Assesses vowel pronunciation by comparing expected vs actual phonemes.
    
    Provides:
    - Overall pronunciation score
    - Vowel-specific accuracy
    - Per-word feedback with timestamps
    - Focus areas for improvement
    """
    
    def __init__(self):
        """Initialize the vowel assessor with g2p for auto phoneme generation."""
        logger.info("Initializing G2P for automatic phoneme generation...")
        self.g2p = G2p()
        logger.info("G2P initialized")
    
    def _text_to_phonemes(self, text: str) -> tuple[str, list[str]]:
        """
        Convert text to expected phonemes using g2p-en.
        
        Args:
            text: English text
            
        Returns:
            Tuple of (phoneme_string, phoneme_list)
        """
        # Get ARPAbet phonemes
        arpabet = self.g2p(text)
        
        # Filter out non-phoneme tokens (spaces, punctuation markers)
        phoneme_list = [p for p in arpabet if p.strip() and not p.startswith(' ')]
        
        # Convert to IPA where possible
        ipa_list = []
        for p in phoneme_list:
            # Remove stress markers (0, 1, 2)
            base_p = re.sub(r'[012]', '', p)
            if base_p in ARPABET_VOWELS:
                ipa_list.append(ARPABET_VOWELS[base_p])
            else:
                ipa_list.append(base_p.lower())
        
        return ' '.join(ipa_list), ipa_list
    
    def _extract_vowels(self, phonemes: list[str]) -> list[str]:
        """Extract only vowel phonemes from a phoneme list."""
        vowels = []
        i = 0
        while i < len(phonemes):
            p = phonemes[i]
            
            # Check for diphthongs (two-character combinations)
            if i + 1 < len(phonemes):
                diphthong = p + phonemes[i + 1]
                if diphthong in IPA_VOWELS:
                    vowels.append(diphthong)
                    i += 2
                    continue
            
            # Check single vowel
            if p in IPA_VOWELS:
                vowels.append(p)
            
            i += 1
        
        return vowels
    
    def _is_vowel(self, phoneme: str) -> bool:
        """Check if a phoneme is a vowel."""
        # Clean phoneme (remove length markers, stress)
        clean = re.sub(r'[ːˈˌ012]', '', phoneme)
        return clean in IPA_VOWELS or any(clean.startswith(v) for v in IPA_VOWELS)
    
    def _compare_vowel_sequences(
        self,
        expected: list[str],
        actual: list[str]
    ) -> tuple[float, list[dict]]:
        """
        Compare expected and actual vowel sequences.
        
        Returns:
            Tuple of (similarity_score, error_list)
        """
        if not expected:
            return 1.0, []
        
        # Use sequence matcher for alignment
        matcher = SequenceMatcher(None, expected, actual)
        ratio = matcher.ratio()
        
        errors = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                for k, (exp, act) in enumerate(zip(expected[i1:i2], actual[j1:j2])):
                    errors.append({
                        'position': i1 + k,
                        'expected': exp,
                        'actual': act,
                        'error_type': 'substitution',
                        'expected_name': IPA_VOWELS.get(exp, {}).get('name', exp),
                        'actual_name': IPA_VOWELS.get(act, {}).get('name', act)
                    })
            elif tag == 'delete':
                for k, exp in enumerate(expected[i1:i2]):
                    errors.append({
                        'position': i1 + k,
                        'expected': exp,
                        'actual': None,
                        'error_type': 'missing',
                        'expected_name': IPA_VOWELS.get(exp, {}).get('name', exp)
                    })
            elif tag == 'insert':
                for k, act in enumerate(actual[j1:j2]):
                    errors.append({
                        'position': i1,
                        'expected': None,
                        'actual': act,
                        'error_type': 'insertion',
                        'actual_name': IPA_VOWELS.get(act, {}).get('name', act)
                    })
        
        return ratio, errors
    
    def _identify_focus_areas(self, errors: list[dict]) -> list[str]:
        """
        Identify vowels that need the most practice.
        
        Based on error frequency and difficulty.
        """
        error_counts = {}
        
        for error in errors:
            if error.get('expected'):
                vowel = error['expected']
                if vowel not in error_counts:
                    error_counts[vowel] = {
                        'count': 0,
                        'name': IPA_VOWELS.get(vowel, {}).get('name', vowel),
                        'example': IPA_VOWELS.get(vowel, {}).get('example', ''),
                        'difficulty': IPA_VOWELS.get(vowel, {}).get('difficulty', 'medium')
                    }
                error_counts[vowel]['count'] += 1
        
        # Sort by count, then by difficulty
        difficulty_order = {'high': 0, 'medium': 1, 'low': 2}
        sorted_vowels = sorted(
            error_counts.items(),
            key=lambda x: (-x[1]['count'], difficulty_order.get(x[1]['difficulty'], 1))
        )
        
        # Return top focus areas with descriptions
        focus_areas = []
        for vowel, info in sorted_vowels[:3]:
            focus_areas.append(
                f"/{vowel}/ ({info['name']}) - as in '{info['example']}' - {info['count']} error(s)"
            )
        
        return focus_areas
    
    def assess(
        self,
        expected_text: str,
        expected_phonemes: Optional[str],
        actual_phonemes: str,
        actual_phoneme_list: list[str],
        word_alignments: list[dict],
        focus_vowels: Optional[list[str]] = None
    ) -> dict:
        """
        Full pronunciation assessment.
        
        Args:
            expected_text: The text the student was supposed to say
            expected_phonemes: Expected IPA phonemes (auto-generated if None)
            actual_phonemes: Actual IPA phonemes from wav2vec2
            actual_phoneme_list: List of actual phonemes
            word_alignments: Word-level timing from WhisperX
            focus_vowels: Optional list of vowels to focus on
            
        Returns:
            Assessment dictionary with scores and feedback
        """
        logger.debug(f"Assessing: '{expected_text}'")
        
        # ALWAYS generate expected phonemes from text to ensure IPA format
        # (passed expected_phonemes may be in ARPAbet format from old data)
        logger.debug("Generating expected phonemes with G2P")
        expected_phonemes, expected_list = self._text_to_phonemes(expected_text)
        
        logger.info(f"Expected phonemes: {expected_phonemes}")
        logger.info(f"Actual phonemes: {actual_phonemes}")
        logger.info(f"Actual phoneme_list: {actual_phoneme_list}")
        
        # Extract vowels
        expected_vowels = self._extract_vowels(expected_list)
        actual_vowels = self._extract_vowels(actual_phoneme_list)
        
        logger.info(f"Expected vowels: {expected_vowels}")
        logger.info(f"Actual vowels: {actual_vowels}")
        
        # Calculate overall phoneme similarity
        overall_matcher = SequenceMatcher(None, expected_list, actual_phoneme_list)
        overall_score = overall_matcher.ratio()
        
        # Calculate vowel-specific score
        vowel_score, vowel_errors = self._compare_vowel_sequences(
            expected_vowels, actual_vowels
        )
        
        # If focus vowels specified, filter/weight errors
        if focus_vowels:
            focus_errors = [
                e for e in vowel_errors 
                if e.get('expected') in focus_vowels or e.get('actual') in focus_vowels
            ]
        else:
            focus_errors = vowel_errors
        
        # Add timestamp info to errors where possible
        vowel_errors_with_timing = []
        for error in vowel_errors:
            error_with_timing = error.copy()
            # Try to match with word alignment
            pos = error.get('position', 0)
            if pos < len(word_alignments):
                word_info = word_alignments[pos] if pos < len(word_alignments) else {}
                error_with_timing['word'] = word_info.get('word', '')
                error_with_timing['timestamp_ms'] = int(word_info.get('start', 0) * 1000)
                error_with_timing['end_timestamp_ms'] = int(word_info.get('end', 0) * 1000)
            vowel_errors_with_timing.append(error_with_timing)
        
        # Build word-by-word details
        word_details = []
        words = expected_text.split()
        for i, word in enumerate(words):
            word_phonemes, word_phoneme_list = self._text_to_phonemes(word)
            word_vowels = self._extract_vowels(word_phoneme_list)
            
            timing = word_alignments[i] if i < len(word_alignments) else {}
            
            word_details.append({
                'word': word,
                'expected_phonemes': word_phonemes,
                'expected_vowels': word_vowels,
                'start_ms': int(timing.get('start', 0) * 1000),
                'end_ms': int(timing.get('end', 0) * 1000),
                'confidence': timing.get('score', 1.0)
            })
        
        # Identify focus areas
        focus_areas = self._identify_focus_areas(vowel_errors)
        
        result = {
            'overall_score': round(overall_score, 3),
            'vowel_score': round(vowel_score, 3),
            'vowel_errors': vowel_errors_with_timing,
            'focus_areas': focus_areas,
            'word_details': word_details,
            'expected_phonemes': expected_phonemes,
            'expected_vowels': expected_vowels,
            'actual_vowels': actual_vowels,
            'total_vowels': len(expected_vowels),
            'correct_vowels': len(expected_vowels) - len([e for e in vowel_errors if e['error_type'] != 'insertion'])
        }
        
        logger.info(
            f"Assessment complete: overall={overall_score:.1%}, "
            f"vowels={vowel_score:.1%}, errors={len(vowel_errors)}"
        )
        
        return result
