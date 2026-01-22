// Type definitions for Pronunciation Trainer

export interface Sentence {
  index: number
  text: string
  expected_phonemes: string
  focus_vowels: string[] | null
}

export interface Exercise {
  exercise_id: string
  original_filename: string
  sentence_count: number
  auto_generated_phonemes: number
  sentences: Sentence[]
}

export interface VowelError {
  position: number
  expected: string | null
  actual: string | null
  error_type: 'substitution' | 'missing' | 'insertion'
  expected_name?: string
  actual_name?: string
  word?: string
  timestamp_ms?: number
  end_timestamp_ms?: number
}

export interface WordDetail {
  word: string
  expected_phonemes: string
  expected_vowels: string[]
  start_ms: number
  end_ms: number
  confidence: number
}

export interface AssessmentResult {
  overall_score: number
  vowel_score: number
  vowel_errors: VowelError[]
  focus_areas: string[]
  word_details: WordDetail[]
  expected_phonemes: string
  expected_vowels: string[]
  actual_vowels: string[]
  total_vowels: number
  correct_vowels: number
}

export interface HealthStatus {
  status: string
  whisper_status: string
  phoneme_status: string
  version: string
}
