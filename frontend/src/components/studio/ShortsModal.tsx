import { useState } from 'react'
import { studioApi } from '../../api/studio'
import { jobsApi } from '../../api/jobs'
import type { Clip } from '../../types/studio'

interface Props {
  assetId: string
  hasShorts: boolean
}

export function ShortsModal({ assetId, hasShorts }: Props) {
  const [open, setOpen] = useState(false)
  const [clips, setClips] = useState<Clip[]>([])
  const [jobId, setJobId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const data = await studioApi.getShorts(assetId)
      setClips(data.clips)
      setJobId(data.job_id)
    } catch {
      setClips([])
    } finally {
      setLoading(false)
    }
  }

  function openModal() {
    setOpen(true)
    load()
  }

  if (!hasShorts) return null

  return (
    <>
      <button
        onClick={openModal}
        className="w-full py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
      >
        View Shorts ({clips.length > 0 ? clips.length : '…'})
      </button>
      {open && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setOpen(false)}>
          <div
            className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h2 className="text-lg font-bold text-gray-900">Generated Shorts</h2>
              <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-gray-600">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="overflow-y-auto p-6">
              {loading ? (
                <p className="text-center text-gray-400 py-8">Loading clips…</p>
              ) : clips.length === 0 ? (
                <p className="text-center text-gray-400 py-8">No clips found.</p>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  {clips.map((clip) => (
                    <ClipCard key={clip.clip_id} clip={clip} jobId={jobId!} />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}

function ClipCard({ clip, jobId }: { clip: Clip; jobId: string }) {
  const src = jobsApi.clipVideoUrl(jobId, clip.clip_id)
  return (
    <div className="bg-gray-50 rounded-xl overflow-hidden border border-gray-200">
      <video controls className="w-full bg-black" src={src} />
      <div className="p-3">
        <p className="text-xs text-gray-600 line-clamp-2 mb-2">{clip.text}</p>
        <div className="flex items-center justify-between text-xs text-gray-400">
          <span>{clip.duration.toFixed(1)}s</span>
          {clip.speaker && <span>{clip.speaker}</span>}
          <span>Score {clip.score.toFixed(2)}</span>
        </div>
      </div>
    </div>
  )
}
