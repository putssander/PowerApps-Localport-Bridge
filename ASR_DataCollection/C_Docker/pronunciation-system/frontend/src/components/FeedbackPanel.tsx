import { useState } from 'react'
import { CheckCircle, XCircle, AlertTriangle, Target, TrendingUp, ChevronDown, ChevronUp, Volume2, Info } from 'lucide-react'
import type { AssessmentResult, VowelError } from '../types'

interface FeedbackPanelProps {
  assessment: AssessmentResult | null
  isProcessing: boolean
}

// Map IPA vowels to example words and approximate letter representations
const VOWEL_HELP: Record<string, { letters: string; example: string; tip: string }> = {
  'ɪ': { letters: 'i', example: 'bit, sit', tip: 'Short "i" - quick and relaxed' },
  'ɛ': { letters: 'e', example: 'bet, red', tip: 'Short "e" - mouth slightly open' },
  'æ': { letters: 'a', example: 'cat, bat', tip: 'Short "a" - wide open mouth' },
  'ɑ': { letters: 'o/a', example: 'hot, father', tip: 'Open "ah" sound - jaw drops' },
  'ʌ': { letters: 'u', example: 'but, cup', tip: 'Short "uh" - relaxed, central' },
  'ʊ': { letters: 'oo', example: 'book, put', tip: 'Short "oo" - lips slightly rounded' },
  'ə': { letters: 'a/e/i/o/u', example: 'about, the', tip: 'Schwa - weak, unstressed vowel' },
  'i': { letters: 'ee', example: 'see, beat', tip: 'Long "ee" - smile position' },
  'iː': { letters: 'ee', example: 'see, beat', tip: 'Long "ee" - smile position' },
  'u': { letters: 'oo', example: 'boot, food', tip: 'Long "oo" - lips rounded' },
  'uː': { letters: 'oo', example: 'boot, food', tip: 'Long "oo" - lips rounded' },
  'ɔ': { letters: 'aw', example: 'law, thought', tip: 'Open "aw" - rounded lips' },
  'ɔː': { letters: 'aw', example: 'law, thought', tip: 'Open "aw" - rounded lips' },
  'ɜ': { letters: 'er/ir/ur', example: 'bird, her', tip: 'R-colored vowel' },
  'ɜː': { letters: 'er/ir/ur', example: 'bird, her', tip: 'R-colored vowel' },
  'eɪ': { letters: 'ay/ai', example: 'say, wait', tip: 'Diphthong - "eh" to "ee"' },
  'oʊ': { letters: 'ow/o', example: 'go, boat', tip: 'Diphthong - "oh" to "oo"' },
  'aɪ': { letters: 'i/y', example: 'my, bite', tip: 'Diphthong - "ah" to "ee"' },
  'aʊ': { letters: 'ow/ou', example: 'how, out', tip: 'Diphthong - "ah" to "oo"' },
  'ɔɪ': { letters: 'oy/oi', example: 'boy, coin', tip: 'Diphthong - "aw" to "ee"' },
}

export default function FeedbackPanel({ assessment, isProcessing }: FeedbackPanelProps) {
  const [showPhonemeDetails, setShowPhonemeDetails] = useState(false)
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false)

  if (isProcessing) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Feedback</h2>
        <div className="flex flex-col items-center justify-center py-8">
          <div className="animate-spin w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full mb-4" />
          <p className="text-gray-500">Analyzing your pronunciation...</p>
        </div>
      </div>
    )
  }

  if (!assessment) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Feedback</h2>
        <div className="text-center py-8 text-gray-500">
          <Target className="w-12 h-12 mx-auto mb-4 text-gray-300" />
          <p>Record a sentence to receive pronunciation feedback</p>
        </div>
      </div>
    )
  }

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600'
    if (score >= 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getScoreBg = (score: number) => {
    if (score >= 0.8) return 'bg-green-500'
    if (score >= 0.6) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const getScoreEmoji = (score: number) => {
    if (score >= 0.9) return '🌟'
    if (score >= 0.8) return '😊'
    if (score >= 0.6) return '🤔'
    if (score >= 0.4) return '😕'
    return '💪'
  }

  const getScoreMessage = (score: number) => {
    if (score >= 0.9) return 'Excellent! Near-perfect pronunciation!'
    if (score >= 0.8) return 'Great job! Just a few small improvements needed.'
    if (score >= 0.6) return 'Good effort! Focus on the highlighted areas.'
    if (score >= 0.4) return 'Keep practicing! Pay attention to the vowels below.'
    return "Don't give up! Let's work on the basics."
  }

  // Build word-level error map for highlighting
  const wordErrors = new Map<number, { vowelErrors: VowelError[]; hasError: boolean }>()
  
  // Match errors to words based on word field or position
  assessment.word_details.forEach((word, idx) => {
    const errorsForWord = assessment.vowel_errors.filter(
      err => err.word?.toLowerCase() === word.word.toLowerCase()
    )
    wordErrors.set(idx, {
      vowelErrors: errorsForWord,
      hasError: errorsForWord.length > 0
    })
  })

  // If no errors matched by word name, try to distribute by position
  if (assessment.vowel_errors.length > 0 && !Array.from(wordErrors.values()).some(w => w.hasError)) {
    let vowelPosition = 0
    assessment.word_details.forEach((word, idx) => {
      const wordVowelCount = word.expected_vowels.length
      const errorsInRange = assessment.vowel_errors.filter(
        err => err.position !== undefined && err.position >= vowelPosition && err.position < vowelPosition + wordVowelCount
      )
      if (errorsInRange.length > 0) {
        wordErrors.set(idx, { vowelErrors: errorsInRange, hasError: true })
      }
      vowelPosition += wordVowelCount
    })
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6 space-y-5">
      <h2 className="text-lg font-semibold text-gray-900">Feedback</h2>

      {/* Score Summary - Simplified & Friendly */}
      <div className="text-center p-5 bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl">
        <div className="text-5xl mb-2">{getScoreEmoji(assessment.vowel_score)}</div>
        <p className={`text-4xl font-bold ${getScoreColor(assessment.vowel_score)}`}>
          {Math.round(assessment.vowel_score * 100)}%
        </p>
        <p className="text-sm text-gray-600 mt-2">{getScoreMessage(assessment.vowel_score)}</p>
        <div className="flex items-center justify-center gap-4 mt-3 text-sm">
          <span className="text-gray-500">
            <span className="font-semibold text-gray-700">{assessment.correct_vowels}</span> of {assessment.total_vowels} vowels correct
          </span>
        </div>
        {/* Progress bar */}
        <div className="h-2 bg-gray-200 rounded-full mt-3 overflow-hidden max-w-xs mx-auto">
          <div
            className={`h-full transition-all duration-500 ${getScoreBg(assessment.vowel_score)}`}
            style={{ width: `${assessment.vowel_score * 100}%` }}
          />
        </div>
      </div>

      {/* PRIMARY FEEDBACK: Sentence with Highlighted Words */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h3 className="font-medium text-gray-700 mb-3 flex items-center gap-2">
          <Volume2 className="w-5 h-5 text-indigo-500" />
          Your Sentence
        </h3>
        <div className="flex flex-wrap gap-2 text-lg leading-relaxed">
          {assessment.word_details.map((word, idx) => {
            const errorInfo = wordErrors.get(idx)
            const hasError = errorInfo?.hasError || false
            const errors = errorInfo?.vowelErrors || []
            
            return (
              <div key={idx} className="relative group">
                <span
                  className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg transition-all cursor-default ${
                    hasError
                      ? 'bg-red-100 border-2 border-red-300 text-red-800 font-medium'
                      : 'bg-green-100 border-2 border-green-200 text-green-800'
                  }`}
                >
                  {word.word}
                  {hasError ? (
                    <XCircle className="w-4 h-4 text-red-500" />
                  ) : (
                    <CheckCircle className="w-4 h-4 text-green-500" />
                  )}
                </span>
                
                {/* Tooltip for words with errors */}
                {hasError && errors.length > 0 && (
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-10">
                    <div className="bg-gray-900 text-white text-xs rounded-lg px-3 py-2 whitespace-nowrap">
                      {errors.map((e, i) => (
                        <div key={i}>
                          {e.error_type === 'substitution' && (
                            <span>Say /{e.expected}/ not /{e.actual}/</span>
                          )}
                          {e.error_type === 'missing' && (
                            <span>Missing: /{e.expected}/</span>
                          )}
                        </div>
                      ))}
                      <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
        
        <div className="flex gap-4 mt-3 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 bg-green-200 border border-green-300 rounded" /> Correct
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 bg-red-200 border border-red-300 rounded" /> Needs practice
          </span>
        </div>
      </div>

      {/* What to Improve - User-Friendly */}
      {assessment.vowel_errors.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <h3 className="font-medium text-amber-900 mb-3 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            How to Improve
          </h3>
          <div className="space-y-3">
            {/* Group errors by expected vowel for clearer feedback */}
            {Array.from(new Set(assessment.vowel_errors.filter(e => e.expected).map(e => e.expected))).slice(0, 3).map((vowel, idx) => {
              const vowelHelp = VOWEL_HELP[vowel!]
              const errorsForVowel = assessment.vowel_errors.filter(e => e.expected === vowel)
              
              return (
                <div key={idx} className="bg-white rounded-lg p-3 border border-amber-100">
                  <div className="flex items-start gap-3">
                    <span className="text-2xl font-mono bg-amber-100 px-3 py-1 rounded-lg text-amber-800 flex-shrink-0">
                      {vowelHelp?.letters || vowel}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-800">
                        Practice the "{vowelHelp?.letters || vowel}" sound
                      </p>
                      {vowelHelp && (
                        <>
                          <p className="text-sm text-gray-600 mt-1">
                            Like in: <span className="font-medium">{vowelHelp.example}</span>
                          </p>
                          <p className="text-xs text-amber-700 mt-1 flex items-start gap-1">
                            <Info className="w-3 h-3 mt-0.5 flex-shrink-0" />
                            <span>{vowelHelp.tip}</span>
                          </p>
                        </>
                      )}
                      {errorsForVowel[0]?.word && (
                        <p className="text-xs text-gray-500 mt-1">
                          Found in: "<span className="font-medium">{errorsForVowel[0].word}</span>"
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Success message */}
      {assessment.vowel_errors.length === 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center gap-3">
          <CheckCircle className="w-10 h-10 text-green-500 flex-shrink-0" />
          <div>
            <p className="font-medium text-green-900 text-lg">Perfect! 🎉</p>
            <p className="text-sm text-green-700">All vowels pronounced correctly. Great job!</p>
          </div>
        </div>
      )}

      {/* Collapsible: Detailed Vowel Errors */}
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <button
          onClick={() => setShowPhonemeDetails(!showPhonemeDetails)}
          className="w-full px-4 py-3 bg-gray-50 flex items-center justify-between text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
        >
          <span className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            Detailed Errors ({assessment.vowel_errors.length})
          </span>
          {showPhonemeDetails ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>
        
        {showPhonemeDetails && (
          <div className="p-4 space-y-2 max-h-[200px] overflow-y-auto bg-white">
            {assessment.vowel_errors.length === 0 ? (
              <p className="text-gray-500 text-sm text-center py-4">No errors to display</p>
            ) : (
              assessment.vowel_errors.map((error, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg text-sm ${
                    error.error_type === 'substitution'
                      ? 'bg-red-50 border border-red-200'
                      : error.error_type === 'missing'
                      ? 'bg-yellow-50 border border-yellow-200'
                      : 'bg-orange-50 border border-orange-200'
                  }`}
                >
                  <div className="flex items-center gap-2 flex-wrap">
                    {error.error_type === 'substitution' && (
                      <>
                        <span className="text-gray-600">You said</span>
                        <span className="font-mono bg-red-200 px-2 py-1 rounded">/{error.actual}/</span>
                        <span className="text-gray-400">instead of</span>
                        <span className="font-mono bg-green-200 px-2 py-1 rounded">/{error.expected}/</span>
                        {error.expected_name && (
                          <span className="text-xs text-gray-500">({error.expected_name})</span>
                        )}
                      </>
                    )}
                    {error.error_type === 'missing' && (
                      <span className="text-yellow-800">
                        Missing: <span className="font-mono bg-yellow-200 px-1 rounded">/{error.expected}/</span>
                        {error.expected_name && <span className="text-xs ml-1">({error.expected_name})</span>}
                      </span>
                    )}
                    {error.error_type === 'insertion' && (
                      <span className="text-orange-800">
                        Extra: <span className="font-mono bg-orange-200 px-1 rounded">/{error.actual}/</span>
                      </span>
                    )}
                  </div>
                  {error.word && (
                    <p className="text-xs text-gray-500 mt-1">In word: "<span className="font-medium">{error.word}</span>"</p>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Collapsible: Technical Phoneme Info */}
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <button
          onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
          className="w-full px-4 py-3 bg-gray-50 flex items-center justify-between text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
        >
          <span className="flex items-center gap-2">
            <Info className="w-4 h-4" />
            Technical Details
          </span>
          {showTechnicalDetails ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>
        
        {showTechnicalDetails && (
          <div className="p-4 space-y-3 bg-white text-sm">
            <div>
              <p className="text-gray-500 text-xs mb-1">Expected vowels:</p>
              <div className="flex flex-wrap gap-1">
                {assessment.expected_vowels.map((v, i) => (
                  <span key={i} className="font-mono text-xs bg-indigo-100 px-2 py-1 rounded">/{v}/</span>
                ))}
              </div>
            </div>
            <div>
              <p className="text-gray-500 text-xs mb-1">Your vowels:</p>
              <div className="flex flex-wrap gap-1">
                {assessment.actual_vowels.map((v, i) => (
                  <span key={i} className="font-mono text-xs bg-purple-100 px-2 py-1 rounded">/{v}/</span>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 pt-2 border-t">
              <div>
                <p className="text-gray-500 text-xs">Overall Score</p>
                <p className={`font-bold ${getScoreColor(assessment.overall_score)}`}>
                  {Math.round(assessment.overall_score * 100)}%
                </p>
              </div>
              <div>
                <p className="text-gray-500 text-xs">Vowel Score</p>
                <p className={`font-bold ${getScoreColor(assessment.vowel_score)}`}>
                  {Math.round(assessment.vowel_score * 100)}%
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
