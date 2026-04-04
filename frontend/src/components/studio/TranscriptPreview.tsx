import { useState, useEffect } from 'react'
import { studioApi } from '../../api/studio'
import type { TranscriptSegment } from '../../types/studio'

interface Props {
  assetId: string
  hasTranscript: boolean
}

export function TranscriptPreview({ assetId, hasTranscript }: Props) {
  const [segments, setSegments] = useState<TranscriptSegment[]>([])
  const [expanded, setExpanded] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!hasTranscript) return
    setLoading(true)
    studioApi.getTranscript(assetId)
      .then((d) => setSegments(d.segments))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [assetId, hasTranscript])

  if (!hasTranscript) return null

  const visible = expanded ? segments : segments.slice(0, 5)

  return (
    <div>
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Transcript</h3>
      {loading ? (
        <p className="text-sm text-gray-400">Loading…</p>
      ) : (
        <div className="space-y-1">
          {visible.map((s, i) => (
            <div key={i} className="flex gap-2 text-sm">
              <span className="text-gray-400 font-mono text-xs shrink-0 mt-0.5">
                {Math.floor(s.start / 60)}:{String(Math.floor(s.start % 60)).padStart(2, '0')}
              </span>
              <p className="text-gray-700">{s.text}</p>
            </div>
          ))}
          {segments.length > 5 && (
            <button
              onClick={() => setExpanded((e) => !e)}
              className="text-xs text-blue-600 hover:underline mt-1"
            >
              {expanded ? 'Show less' : `Show all ${segments.length} segments`}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
