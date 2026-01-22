import { ChevronRight } from 'lucide-react'
import type { Exercise, Sentence } from '../types'

interface ExercisePanelProps {
  exercise: Exercise
  currentSentence: Sentence | null
  onSentenceSelect: (sentence: Sentence) => void
}

export default function ExercisePanel({ exercise, currentSentence, onSentenceSelect }: ExercisePanelProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-gray-900">{exercise.original_filename}</h2>
        <p className="text-sm text-gray-500">{exercise.sentence_count} sentences</p>
      </div>

      <div className="space-y-2 max-h-[400px] overflow-y-auto">
        {exercise.sentences.map((sentence) => (
          <button
            key={sentence.index}
            onClick={() => onSentenceSelect(sentence)}
            className={`w-full text-left p-3 rounded-lg transition-colors flex items-center gap-3 ${
              currentSentence?.index === sentence.index
                ? 'bg-indigo-100 border-2 border-indigo-300'
                : 'bg-gray-50 hover:bg-gray-100 border-2 border-transparent'
            }`}
          >
            <span className={`w-6 h-6 rounded-full flex items-center justify-center text-sm font-medium ${
              currentSentence?.index === sentence.index
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-200 text-gray-600'
            }`}>
              {sentence.index}
            </span>
            <span className={`flex-1 text-sm truncate ${
              currentSentence?.index === sentence.index
                ? 'text-indigo-900 font-medium'
                : 'text-gray-700'
            }`}>
              {sentence.text}
            </span>
            {currentSentence?.index === sentence.index && (
              <ChevronRight className="w-5 h-5 text-indigo-600" />
            )}
          </button>
        ))}
      </div>
    </div>
  )
}
