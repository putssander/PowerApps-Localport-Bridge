import { useState, useCallback } from 'react'
import { Mic, Upload, BookOpen } from 'lucide-react'
import AudioRecorder from './components/AudioRecorder'
import ExercisePanel from './components/ExercisePanel'
import FeedbackPanel from './components/FeedbackPanel'
import ExerciseUploader from './components/ExerciseUploader'
import type { Exercise, AssessmentResult, Sentence } from './types'

type Tab = 'practice' | 'exercises' | 'upload'

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('practice')
  const [currentExercise, setCurrentExercise] = useState<Exercise | null>(null)
  const [currentSentence, setCurrentSentence] = useState<Sentence | null>(null)
  const [assessment, setAssessment] = useState<AssessmentResult | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  const handleExerciseSelect = useCallback((exercise: Exercise) => {
    setCurrentExercise(exercise)
    if (exercise.sentences.length > 0) {
      setCurrentSentence(exercise.sentences[0])
    }
    setAssessment(null)
    setActiveTab('practice')
  }, [])

  const handleSentenceSelect = useCallback((sentence: Sentence) => {
    setCurrentSentence(sentence)
    setAssessment(null)
  }, [])

  const handleRecordingComplete = useCallback(async (audioBlob: Blob) => {
    if (!currentSentence) return

    setIsProcessing(true)
    setAssessment(null)

    try {
      // Convert blob to base64
      const reader = new FileReader()
      const base64Promise = new Promise<string>((resolve) => {
        reader.onloadend = () => {
          const base64 = (reader.result as string).split(',')[1]
          resolve(base64)
        }
      })
      reader.readAsDataURL(audioBlob)
      const base64Audio = await base64Promise

      // Call assessment API
      const response = await fetch('/api/assess', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_name: `assessment_${Date.now()}`,
          base64_audio: base64Audio,
          expected_text: currentSentence.text,
          expected_phonemes: currentSentence.expected_phonemes,
          focus_vowels: currentSentence.focus_vowels
        })
      })

      if (!response.ok) {
        throw new Error('Assessment failed')
      }

      const result = await response.json()
      setAssessment(result.phoneme_assessment)
    } catch (error) {
      console.error('Assessment error:', error)
      alert('Failed to assess pronunciation. Please try again.')
    } finally {
      setIsProcessing(false)
    }
  }, [currentSentence])

  const handleExerciseUploaded = useCallback((exercise: Exercise) => {
    setCurrentExercise(exercise)
    if (exercise.sentences.length > 0) {
      setCurrentSentence(exercise.sentences[0])
    }
    setActiveTab('practice')
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center">
                <Mic className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Pronunciation Trainer</h1>
                <p className="text-sm text-gray-500">English Vowel Practice</p>
              </div>
            </div>

            {/* Tab Navigation */}
            <nav className="flex gap-1 bg-gray-100 p-1 rounded-lg">
              <button
                onClick={() => setActiveTab('practice')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${
                  activeTab === 'practice'
                    ? 'bg-white text-indigo-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <Mic className="w-4 h-4" />
                Practice
              </button>
              <button
                onClick={() => setActiveTab('exercises')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${
                  activeTab === 'exercises'
                    ? 'bg-white text-indigo-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <BookOpen className="w-4 h-4" />
                Exercises
              </button>
              <button
                onClick={() => setActiveTab('upload')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${
                  activeTab === 'upload'
                    ? 'bg-white text-indigo-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <Upload className="w-4 h-4" />
                Upload
              </button>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {activeTab === 'practice' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Panel - Exercise & Sentence */}
            <div className="lg:col-span-1 space-y-6">
              {currentExercise ? (
                <ExercisePanel
                  exercise={currentExercise}
                  currentSentence={currentSentence}
                  onSentenceSelect={handleSentenceSelect}
                />
              ) : (
                <div className="bg-white rounded-xl shadow-sm p-6 text-center">
                  <BookOpen className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-700 mb-2">No Exercise Selected</h3>
                  <p className="text-gray-500 mb-4">
                    Upload an XLSX file or select an existing exercise to start practicing.
                  </p>
                  <button
                    onClick={() => setActiveTab('exercises')}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                  >
                    Browse Exercises
                  </button>
                </div>
              )}
            </div>

            {/* Center Panel - Recording */}
            <div className="lg:col-span-1">
              <AudioRecorder
                sentence={currentSentence}
                onRecordingComplete={handleRecordingComplete}
                isProcessing={isProcessing}
              />
            </div>

            {/* Right Panel - Feedback */}
            <div className="lg:col-span-1">
              <FeedbackPanel
                assessment={assessment}
                isProcessing={isProcessing}
              />
            </div>
          </div>
        )}

        {activeTab === 'exercises' && (
          <ExerciseList onSelect={handleExerciseSelect} />
        )}

        {activeTab === 'upload' && (
          <ExerciseUploader onUploaded={handleExerciseUploaded} />
        )}
      </main>
    </div>
  )
}

// Exercise List Component
function ExerciseList({ onSelect }: { onSelect: (exercise: Exercise) => void }) {
  const [exercises, setExercises] = useState<Exercise[]>([])
  const [loading, setLoading] = useState(true)

  useState(() => {
    fetch('/api/exercises')
      .then(res => res.json())
      .then(data => {
        setExercises(data.exercises || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  })

  const handleSelect = async (exerciseId: string) => {
    try {
      const response = await fetch(`/api/exercises/${exerciseId}`)
      const exercise = await response.json()
      onSelect(exercise)
    } catch (error) {
      console.error('Failed to load exercise:', error)
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-8 text-center">
        <div className="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full mx-auto"></div>
        <p className="text-gray-500 mt-4">Loading exercises...</p>
      </div>
    )
  }

  if (exercises.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-8 text-center">
        <BookOpen className="w-16 h-16 text-gray-300 mx-auto mb-4" />
        <h3 className="text-xl font-medium text-gray-700 mb-2">No Exercises Found</h3>
        <p className="text-gray-500">Upload an XLSX file to create your first exercise.</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {exercises.map((exercise) => (
        <button
          key={exercise.exercise_id}
          onClick={() => handleSelect(exercise.exercise_id)}
          className="bg-white rounded-xl shadow-sm p-6 text-left hover:shadow-md transition-shadow border-2 border-transparent hover:border-indigo-200"
        >
          <div className="flex items-start justify-between mb-3">
            <BookOpen className="w-8 h-8 text-indigo-600" />
            <span className="text-sm bg-indigo-100 text-indigo-700 px-2 py-1 rounded">
              {exercise.sentence_count} sentences
            </span>
          </div>
          <h3 className="font-medium text-gray-900 truncate">{exercise.original_filename}</h3>
          <p className="text-sm text-gray-500 mt-1">ID: {exercise.exercise_id}</p>
        </button>
      ))}
    </div>
  )
}

export default App
