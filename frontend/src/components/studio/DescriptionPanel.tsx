import { useState, useEffect } from 'react'
import { studioApi } from '../../api/studio'
import type { Description } from '../../types/studio'

interface Props {
  assetId: string
  hasDescription: boolean
}

export function DescriptionPanel({ assetId, hasDescription }: Props) {
  const [desc, setDesc] = useState<Description | null>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!hasDescription) return
    setLoading(true)
    studioApi.getDescription(assetId)
      .then(setDesc)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [assetId, hasDescription])

  if (!hasDescription) return null

  function copy() {
    if (desc?.body) {
      navigator.clipboard.writeText(desc.body)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Description</h3>
        {desc && (
          <button onClick={copy} className="text-xs text-blue-600 hover:underline">
            {copied ? 'Copied!' : 'Copy'}
          </button>
        )}
      </div>
      {loading ? (
        <p className="text-sm text-gray-400">Loading…</p>
      ) : desc ? (
        <pre className="whitespace-pre-wrap text-sm text-gray-700 bg-gray-50 rounded-lg p-3 border border-gray-200 font-sans leading-relaxed max-h-48 overflow-y-auto">
          {desc.body}
        </pre>
      ) : null}
    </div>
  )
}
