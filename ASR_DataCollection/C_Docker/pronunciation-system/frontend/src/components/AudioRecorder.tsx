import { useState, useRef, useEffect, useCallback } from 'react'
import { Mic, Square, Volume2 } from 'lucide-react'
import WaveSurfer from 'wavesurfer.js'
import type { Sentence } from '../types'

interface AudioRecorderProps {
  sentence: Sentence | null
  onRecordingComplete: (audioBlob: Blob) => void
  isProcessing: boolean
}

export default function AudioRecorder({ sentence, onRecordingComplete, isProcessing }: AudioRecorderProps) {
  const [isRecording, setIsRecording] = useState(false)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [duration, setDuration] = useState(0)
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const waveformRef = useRef<HTMLDivElement>(null)
  const wavesurferRef = useRef<WaveSurfer | null>(null)
  const timerRef = useRef<number | null>(null)

  // Initialize WaveSurfer
  useEffect(() => {
    if (waveformRef.current && !wavesurferRef.current) {
      wavesurferRef.current = WaveSurfer.create({
        container: waveformRef.current,
        waveColor: '#c7d2fe',
        progressColor: '#6366f1',
        cursorColor: '#4f46e5',
        height: 80,
        barWidth: 3,
        barGap: 2,
        barRadius: 3,
      })
    }

    return () => {
      if (wavesurferRef.current) {
        wavesurferRef.current.destroy()
        wavesurferRef.current = null
      }
    }
  }, [])

  // Load audio into waveform when blob changes
  useEffect(() => {
    if (audioBlob && wavesurferRef.current) {
      const url = URL.createObjectURL(audioBlob)
      wavesurferRef.current.load(url)
      return () => URL.revokeObjectURL(url)
    }
  }, [audioBlob])

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      })
      
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []
      
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data)
        }
      }
      
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        setAudioBlob(blob)
        stream.getTracks().forEach(track => track.stop())
      }
      
      mediaRecorder.start(100) // Collect data every 100ms
      setIsRecording(true)
      setDuration(0)
      setAudioBlob(null)
      
      // Start timer
      const startTime = Date.now()
      timerRef.current = window.setInterval(() => {
        setDuration(Math.floor((Date.now() - startTime) / 1000))
      }, 100)
      
    } catch (error) {
      console.error('Failed to start recording:', error)
      alert('Failed to access microphone. Please check permissions.')
    }
  }, [])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
    }
  }, [isRecording])

  const playRecording = useCallback(() => {
    if (wavesurferRef.current) {
      wavesurferRef.current.playPause()
    }
  }, [])

  const submitRecording = useCallback(() => {
    if (audioBlob) {
      onRecordingComplete(audioBlob)
    }
  }, [audioBlob, onRecordingComplete])

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Record Your Voice</h2>
      
      {/* Sentence to read */}
      {sentence ? (
        <div className="bg-indigo-50 rounded-lg p-4 mb-6">
          <p className="text-sm text-indigo-600 font-medium mb-1">Read this sentence:</p>
          <p className="text-xl text-gray-900 font-medium">{sentence.text}</p>
          {sentence.focus_vowels && sentence.focus_vowels.length > 0 && (
            <p className="text-sm text-indigo-500 mt-2">
              Focus on: {sentence.focus_vowels.join(', ')}
            </p>
          )}
        </div>
      ) : (
        <div className="bg-gray-50 rounded-lg p-4 mb-6 text-center text-gray-500">
          Select a sentence to practice
        </div>
      )}

      {/* Waveform */}
      <div className="waveform-container bg-gray-50 rounded-lg p-4 mb-4 min-h-[100px]">
        <div ref={waveformRef} />
        {!audioBlob && !isRecording && (
          <div className="flex items-center justify-center h-20 text-gray-400">
            Waveform will appear here after recording
          </div>
        )}
      </div>

      {/* Recording indicator */}
      {isRecording && (
        <div className="flex items-center justify-center gap-3 mb-4">
          <div className="w-3 h-3 bg-red-500 rounded-full recording-pulse" />
          <span className="text-red-600 font-medium">Recording... {formatDuration(duration)}</span>
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center justify-center gap-4">
        {!isRecording ? (
          <button
            onClick={startRecording}
            disabled={!sentence || isProcessing}
            className={`w-16 h-16 rounded-full flex items-center justify-center transition-all ${
              !sentence || isProcessing
                ? 'bg-gray-200 cursor-not-allowed'
                : 'bg-indigo-600 hover:bg-indigo-700 hover:scale-105'
            }`}
          >
            <Mic className={`w-8 h-8 ${!sentence || isProcessing ? 'text-gray-400' : 'text-white'}`} />
          </button>
        ) : (
          <button
            onClick={stopRecording}
            className="w-16 h-16 bg-red-500 hover:bg-red-600 rounded-full flex items-center justify-center transition-all hover:scale-105"
          >
            <Square className="w-8 h-8 text-white" />
          </button>
        )}

        {audioBlob && !isRecording && (
          <>
            <button
              onClick={playRecording}
              disabled={isProcessing}
              className="w-12 h-12 bg-gray-100 hover:bg-gray-200 rounded-full flex items-center justify-center transition-colors"
            >
              <Volume2 className="w-6 h-6 text-gray-600" />
            </button>
            
            <button
              onClick={submitRecording}
              disabled={isProcessing}
              className={`px-6 py-3 rounded-lg font-medium transition-colors ${
                isProcessing
                  ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                  : 'bg-green-600 text-white hover:bg-green-700'
              }`}
            >
              {isProcessing ? 'Analyzing...' : 'Check Pronunciation'}
            </button>
          </>
        )}
      </div>

      {/* Processing indicator */}
      {isProcessing && (
        <div className="mt-4 bg-blue-50 rounded-lg p-4 processing-indicator">
          <div className="flex items-center justify-center gap-3">
            <div className="animate-spin w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full" />
            <span className="text-blue-700 font-medium">Analyzing your pronunciation...</span>
          </div>
        </div>
      )}
    </div>
  )
}
