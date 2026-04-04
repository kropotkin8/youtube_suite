import { useState, useEffect, useCallback } from 'react'
import type { AssetListItem } from '../../types/studio'
import { VideoPlayer } from './VideoPlayer'
import { ActionButtons } from './ActionButtons'
import { TranscriptPreview } from './TranscriptPreview'
import { DescriptionPanel } from './DescriptionPanel'
import { ShortsModal } from './ShortsModal'
import { JobWatcher } from './JobWatcher'

interface Props {
  asset: AssetListItem
  onRefresh: () => void
}

interface ActiveJob {
  jobId: string
  label: string
}

export function AssetDetail({ asset, onRefresh }: Props) {
  const [activeJobs, setActiveJobs] = useState<ActiveJob[]>([])
  // Refresh asset list item flags when a job completes
  const [version, setVersion] = useState(0)

  // Reset jobs on asset switch
  useEffect(() => {
    setActiveJobs([])
  }, [asset.id])

  function onJobStarted(jobId: string, label: string) {
    setActiveJobs((prev) => [...prev, { jobId, label }])
  }

  const handleJobDone = useCallback(
    (jobId: string) => {
      setActiveJobs((prev) => prev.filter((j) => j.jobId !== jobId))
      onRefresh()
      setVersion((v) => v + 1)
    },
    [onRefresh]
  )

  // Re-fetch asset state after a job completes (to refresh flags)
  const [liveAsset, setLiveAsset] = useState<AssetListItem>(asset)
  useEffect(() => {
    setLiveAsset(asset)
  }, [asset, version])

  return (
    <div className="h-full overflow-y-auto space-y-5 pr-1">
      {/* Active job watchers (render nothing) */}
      {activeJobs.map((j) => (
        <JobWatcher
          key={j.jobId}
          jobId={j.jobId}
          label={j.label}
          onDone={() => handleJobDone(j.jobId)}
        />
      ))}

      {/* Title */}
      <div>
        <h2 className="text-lg font-bold text-gray-900 leading-snug">
          {liveAsset.title || liveAsset.filename}
        </h2>
        {liveAsset.market_video_id && (
          <a
            href={`https://youtube.com/watch?v=${liveAsset.market_video_id}`}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-blue-500 hover:underline"
          >
            YouTube: {liveAsset.market_video_id}
          </a>
        )}
      </div>

      {/* Video player */}
      <VideoPlayer assetId={liveAsset.id} hasSubtitled={liveAsset.has_transcript} />

      {/* Pipeline actions */}
      <div>
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Actions</h3>
        <ActionButtons asset={liveAsset} onJobStarted={onJobStarted} onRefresh={onRefresh} />
      </div>

      {/* Divider */}
      <hr className="border-gray-100" />

      {/* Transcript */}
      <TranscriptPreview assetId={liveAsset.id} hasTranscript={liveAsset.has_transcript} />

      {/* Description */}
      <DescriptionPanel assetId={liveAsset.id} hasDescription={liveAsset.has_description} />

      {/* Shorts */}
      {liveAsset.has_shorts && (
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Shorts</h3>
          <ShortsModal assetId={liveAsset.id} hasShorts={liveAsset.has_shorts} />
        </div>
      )}
    </div>
  )
}
