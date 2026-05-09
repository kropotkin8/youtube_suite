import { useState, useEffect } from 'react'
import { studioApi } from '../../api/studio'
import type { ChaptersResult, ChapterInfo } from '../../types/studio'

interface Props {
  assetId: string
  hasChapters: boolean
}

function formatTimestamp(seconds: number): string {
  const total = Math.floor(seconds)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
}

function MethodBadge({ method }: { method: string }) {
  const map: Record<string, { label: string; className: string }> = {
    claude: { label: 'Claude AI', className: 'bg-purple-100 text-purple-700' },
    extractive: { label: 'Extractive', className: 'bg-blue-100 text-blue-700' },
    naive_extractive: { label: 'Fallback', className: 'bg-gray-100 text-gray-500' },
  }
  const { label, className } = map[method] ?? { label: method, className: 'bg-gray-100 text-gray-500' }
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${className}`}>{label}</span>
  )
}

export function ChaptersPanel({ assetId, hasChapters }: Props) {
  const [data, setData] = useState<ChaptersResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null)

  useEffect(() => {
    if (!hasChapters) return
    setLoading(true)
    studioApi.getChapters(assetId)
      .then((r) => setData(r.result))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [assetId, hasChapters])

  if (!hasChapters) return null

  function copyFormat() {
    if (!data?.youtube_format) return
    navigator.clipboard.writeText(data.youtube_format)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Chapters</h3>
          {data && <MethodBadge method={data.titling_method} />}
        </div>
        {data && <span className="text-xs text-gray-400">{data.chapter_count} chapters</span>}
      </div>

      {loading ? (
        <p className="text-sm text-gray-400">Loading…</p>
      ) : data ? (
        <div className="space-y-3">
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-gray-500 font-medium">YouTube Format</span>
              <button onClick={copyFormat} className="text-xs text-blue-600 hover:underline">
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <pre className="whitespace-pre-wrap font-mono text-xs text-gray-700 bg-gray-50 rounded-lg p-3 border border-gray-200 leading-relaxed max-h-40 overflow-y-auto">
              {data.youtube_format}
            </pre>
          </div>

          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-500 w-14">Start</th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-500">Title</th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-gray-500 w-14">Dur.</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.chapters.map((ch: ChapterInfo, idx: number) => (
                  <>
                    <tr
                      key={idx}
                      className="hover:bg-gray-50 cursor-pointer"
                      onClick={() => setExpandedIdx(expandedIdx === idx ? null : idx)}
                    >
                      <td className="px-3 py-2 font-mono text-xs text-gray-500 whitespace-nowrap">
                        {formatTimestamp(ch.start_seconds)}
                      </td>
                      <td className="px-3 py-2 text-gray-800 font-medium">{ch.title}</td>
                      <td className="px-3 py-2 text-right font-mono text-xs text-gray-400 whitespace-nowrap">
                        {formatTimestamp(ch.end_seconds - ch.start_seconds)}
                      </td>
                    </tr>
                    {expandedIdx === idx && (
                      <tr key={`${idx}-text`} className="bg-gray-50">
                        <td colSpan={3} className="px-3 py-2">
                          <p className="text-xs text-gray-500 leading-relaxed">{ch.text}</p>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </div>
  )
}
