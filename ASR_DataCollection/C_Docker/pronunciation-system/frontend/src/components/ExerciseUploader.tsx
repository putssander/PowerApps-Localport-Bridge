import { useState, useCallback } from 'react'
import { Upload, FileSpreadsheet, CheckCircle, AlertCircle, Download } from 'lucide-react'
import type { Exercise } from '../types'

interface ExerciseUploaderProps {
  onUploaded: (exercise: Exercise) => void
}

export default function ExerciseUploader({ onUploaded }: ExerciseUploaderProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const handleDownloadExample = () => {
    window.open('/api/exercises/example/download', '_blank')
  }

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const file = e.dataTransfer.files[0]
    if (file) {
      await uploadFile(file)
    }
  }, [])

  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      await uploadFile(file)
    }
  }, [])

  const uploadFile = async (file: File) => {
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      setError('Please upload an Excel file (.xlsx or .xls)')
      return
    }

    setIsUploading(true)
    setError(null)
    setSuccess(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/exercises/upload', {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Upload failed')
      }

      const result = await response.json()
      
      setSuccess(
        `Successfully uploaded "${file.name}" with ${result.sentence_count} sentences ` +
        `(${result.auto_generated_phonemes} auto-generated phonemes)`
      )

      // Fetch the full exercise data
      const exerciseResponse = await fetch(`/api/exercises/${result.exercise_id}`)
      const exercise = await exerciseResponse.json()
      
      setTimeout(() => {
        onUploaded(exercise)
      }, 2000)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload file')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-xl shadow-sm p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Upload Exercise</h2>
        <p className="text-gray-600 mb-6">
          Upload an Excel file with sentences for pronunciation practice.
        </p>

        {/* Format instructions */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <h3 className="font-medium text-blue-900 mb-2">Expected Format</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li><strong>Column A:</strong> Sentence text (required)</li>
            <li><strong>Column B:</strong> Expected IPA phonemes (optional - auto-generated if empty)</li>
            <li><strong>Column C:</strong> Focus vowels, comma-separated (optional)</li>
          </ul>
          <p className="text-xs text-blue-600 mt-2">
            First row should be headers and will be skipped.
          </p>
          
          {/* Download example button */}
          <button
            onClick={handleDownloadExample}
            className="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            <Download className="w-4 h-4" />
            Download Example File
          </button>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
            isDragging
              ? 'border-indigo-500 bg-indigo-50'
              : 'border-gray-300 hover:border-indigo-400'
          }`}
        >
          {isUploading ? (
            <div className="flex flex-col items-center">
              <div className="animate-spin w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full mb-4" />
              <p className="text-gray-600">Processing file...</p>
            </div>
          ) : (
            <>
              <FileSpreadsheet className={`w-16 h-16 mx-auto mb-4 ${
                isDragging ? 'text-indigo-500' : 'text-gray-400'
              }`} />
              <p className="text-lg font-medium text-gray-700 mb-2">
                Drag and drop your XLSX file here
              </p>
              <p className="text-gray-500 mb-4">or</p>
              <label className="cursor-pointer">
                <span className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors inline-flex items-center gap-2">
                  <Upload className="w-5 h-5" />
                  Browse Files
                </span>
                <input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </label>
            </>
          )}
        </div>

        {/* Error message */}
        {error && (
          <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-red-900">Upload Failed</p>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        )}

        {/* Success message */}
        {success && (
          <div className="mt-4 bg-green-50 border border-green-200 rounded-lg p-4 flex items-start gap-3">
            <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-green-900">Upload Successful!</p>
              <p className="text-sm text-green-700">{success}</p>
              <p className="text-xs text-green-600 mt-1">Redirecting to practice...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
