import { useState, useRef } from 'react'
import { studioApi } from '../../api/studio'

interface Props {
  onUploaded: () => void
}

export function DropZone({ onUploaded }: Props) {
  const [dragging, setDragging] = useState(false)
  const [progress, setProgress] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function upload(file: File) {
    setError(null)
    setProgress(0)
    try {
      await studioApi.uploadAsset(file, setProgress)
      onUploaded()
    } catch (e: any) {
      setError(e.message ?? 'Upload failed')
    } finally {
      setProgress(null)
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) upload(file)
  }

  return (
    <div>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={[
          'border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors',
          dragging ? 'border-brand bg-red-50' : 'border-gray-300 hover:border-gray-400',
        ].join(' ')}
      >
        <input
          ref={inputRef}
          type="file"
          accept="video/*"
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f) }}
        />
        <svg className="w-8 h-8 mx-auto mb-2 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
        </svg>
        {progress !== null ? (
          <div>
            <p className="text-sm text-gray-600 mb-2">Uploading… {progress}%</p>
            <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div className="h-full bg-brand rounded-full transition-all" style={{ width: `${progress}%` }} />
            </div>
          </div>
        ) : (
          <>
            <p className="text-sm font-medium text-gray-700">Drop a video or click to browse</p>
            <p className="text-xs text-gray-400 mt-1">MP4, MOV, MKV and other video formats</p>
          </>
        )}
      </div>
      {error && <p className="text-xs text-red-500 mt-2">{error}</p>}
    </div>
  )
}
