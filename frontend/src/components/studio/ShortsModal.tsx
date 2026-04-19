import { useState } from 'react'
import { studioApi } from '../../api/studio'
import { jobsApi } from '../../api/jobs'
import type { Clip, ScoreBreakdown } from '../../types/studio'
import { ScoreSliders } from './ScoreSliders'

interface Props {
  assetId: string
  hasShorts: boolean
}

const HOOK_BADGE: Record<string, { label: string; color: string }> = {
  announcement: { label: 'Announcement', color: 'bg-purple-100 text-purple-700' },
  contradiction: { label: 'Plot twist', color: 'bg-orange-100 text-orange-700' },
  question: { label: 'Question', color: 'bg-blue-100 text-blue-700' },
}

export function ShortsModal({ assetId, hasShorts }: Props) {
  const [open, setOpen] = useState(false)
  const [clips, setClips] = useState<Clip[]>([])
  const [jobId, setJobId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [rescoring, setRescoring] = useState(false)

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

  async function handleRescore(weights: Record<string, number>) {
    setRescoring(true)
    try {
      const data = await studioApi.rescoreShorts(assetId, weights)
      setClips(data.clips)
    } finally {
      setRescoring(false)
    }
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
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => setOpen(false)}
        >
          <div
            className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[92vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h2 className="text-lg font-bold text-gray-900">Generated Shorts</h2>
              <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-gray-600">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Sliders */}
            <div className="px-6 py-3 border-b border-gray-100">
              <ScoreSliders onRescore={handleRescore} loading={rescoring} />
            </div>

            {/* Clips grid */}
            <div className="overflow-y-auto p-6 flex-1">
              {loading ? (
                <p className="text-center text-gray-400 py-8">Loading clips…</p>
              ) : clips.length === 0 ? (
                <p className="text-center text-gray-400 py-8">No clips found.</p>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  {clips.map((clip) => (
                    <ClipCard key={clip.clip_id} clip={clip} jobId={jobId!} assetId={assetId} />
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

function ScoreBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-24 text-gray-500 shrink-0">{label}</span>
      <div className="flex-1 bg-gray-100 rounded-full h-1.5">
        <div className={`${color} h-1.5 rounded-full`} style={{ width: `${Math.round(value * 100)}%` }} />
      </div>
      <span className="w-8 text-right font-mono text-gray-400">{(value * 100).toFixed(0)}</span>
    </div>
  )
}

function ClipCard({ clip, jobId, assetId }: { clip: Clip; jobId: string; assetId: string }) {
  const [showVertical, setShowVertical] = useState(false)
  const [generatingTitle, setGeneratingTitle] = useState(false)
  const [title, setTitle] = useState(clip.title)
  const [hashtags, setHashtags] = useState(clip.hashtags)
  const [showBreakdown, setShowBreakdown] = useState(false)

  const src = jobsApi.clipVideoUrl(jobId, clip.clip_id)
  const hook = clip.hook_type ? HOOK_BADGE[clip.hook_type] : null
  const bd: ScoreBreakdown | null = clip.score_breakdown ?? null

  async function handleGenerateTitle() {
    setGeneratingTitle(true)
    try {
      const data = await studioApi.generateClipTitle(assetId, clip.clip_id)
      setTitle(data.title)
      setHashtags(data.hashtags)
    } catch {
      // silent — user can retry
    } finally {
      setGeneratingTitle(false)
    }
  }

  return (
    <div className="bg-gray-50 rounded-xl overflow-hidden border border-gray-200">
      {/* Video */}
      <div className="relative bg-black">
        <video
          controls
          className={`w-full bg-black ${showVertical ? 'aspect-[9/16] object-contain' : ''}`}
          src={showVertical && clip.vertical_path ? jobsApi.clipVideoUrl(jobId, clip.clip_id + '_vertical') : src}
          key={showVertical ? 'v' : 'h'}
        />
        {clip.vertical_filename && (
          <button
            onClick={() => setShowVertical((v) => !v)}
            className="absolute top-2 right-2 bg-black/60 text-white text-xs px-2 py-1 rounded-lg hover:bg-black/80"
          >
            {showVertical ? '16:9' : '9:16'}
          </button>
        )}
      </div>

      <div className="p-3 space-y-2">
        {/* Hook badge */}
        {hook && (
          <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${hook.color}`}>
            {hook.label}
          </span>
        )}

        {/* Title */}
        {title ? (
          <p className="text-sm font-semibold text-gray-800 leading-snug">{title}</p>
        ) : (
          <button
            onClick={handleGenerateTitle}
            disabled={generatingTitle}
            className="text-xs text-blue-600 hover:underline disabled:opacity-50"
          >
            {generatingTitle ? 'Generating…' : '✦ Generate title'}
          </button>
        )}

        {/* Hashtags */}
        {hashtags.length > 0 && (
          <p className="text-xs text-blue-500">{hashtags.join(' ')}</p>
        )}

        {/* Transcript excerpt */}
        <p className="text-xs text-gray-600 line-clamp-2">{clip.text}</p>

        {/* Meta row */}
        <div className="flex items-center justify-between text-xs text-gray-400">
          <span>{clip.duration.toFixed(1)}s</span>
          {clip.speaker && <span>{clip.speaker}</span>}
          <span className="font-semibold text-gray-600">Score {clip.score.toFixed(2)}</span>
        </div>

        {/* Score breakdown toggle */}
        {bd && (
          <div>
            <button
              onClick={() => setShowBreakdown((s) => !s)}
              className="text-xs text-gray-400 hover:text-gray-600"
            >
              {showBreakdown ? '▲ Hide breakdown' : '▼ Score breakdown'}
            </button>
            {showBreakdown && (
              <div className="mt-2 space-y-1">
                <ScoreBar label="Shortability" value={bd.shortability} color="bg-blue-500" />
                <ScoreBar label="Semantic" value={bd.semantic} color="bg-green-500" />
                <ScoreBar label="Hook" value={bd.hook_score} color="bg-purple-500" />
                <ScoreBar label="Speaker chg" value={bd.speaker_change} color="bg-yellow-500" />
                <ScoreBar label="Audio energy" value={bd.audio_energy} color="bg-red-400" />
                <ScoreBar label="Silence" value={bd.silence_ratio} color="bg-gray-400" />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
