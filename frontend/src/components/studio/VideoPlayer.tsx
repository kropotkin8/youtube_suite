import { useState } from 'react'
import { studioApi } from '../../api/studio'

interface Props {
  assetId: string
  hasSubtitled: boolean
}

export function VideoPlayer({ assetId, hasSubtitled }: Props) {
  const [mode, setMode] = useState<'original' | 'subtitled'>('original')
  const src = mode === 'original'
    ? studioApi.videoUrl(assetId)
    : studioApi.subtitledVideoUrl(assetId)

  return (
    <div className="space-y-2">
      {hasSubtitled && (
        <div className="flex gap-2">
          {(['original', 'subtitled'] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={[
                'px-3 py-1 rounded-full text-xs font-medium transition-colors',
                mode === m
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
              ].join(' ')}
            >
              {m === 'original' ? 'Original' : 'Subtitled'}
            </button>
          ))}
        </div>
      )}
      <video
        key={`${assetId}-${mode}`}
        controls
        className="w-full rounded-lg bg-black max-h-64 object-contain"
        src={src}
      />
    </div>
  )
}
