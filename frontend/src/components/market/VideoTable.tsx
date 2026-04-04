import type { MarketVideoListItem } from '../../types/market'
import { formatNumber, formatDate, parseDuration } from '../../lib/formatters'

interface Props {
  videos: MarketVideoListItem[]
  total: number
  page: number
  limit: number
  sortBy: string
  loading: boolean
  onPageChange: (p: number) => void
  onSortChange: (s: string) => void
}

const COLS: { key: string; label: string; sortable: boolean }[] = [
  { key: 'title', label: 'Title', sortable: false },
  { key: 'channel_title', label: 'Channel', sortable: false },
  { key: 'view_count', label: 'Views', sortable: true },
  { key: 'like_count', label: 'Likes', sortable: false },
  { key: 'comment_count', label: 'Comments', sortable: false },
  { key: 'published_at', label: 'Published', sortable: true },
  { key: 'duration', label: 'Duration', sortable: false },
]

export function VideoTable({ videos, total, page, limit, sortBy, loading, onPageChange, onSortChange }: Props) {
  const totalPages = Math.max(1, Math.ceil(total / limit))
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {COLS.map((c) => (
                <th
                  key={c.key}
                  className={[
                    'text-left px-4 py-3 font-semibold text-gray-600 whitespace-nowrap',
                    c.sortable ? 'cursor-pointer hover:text-gray-900 select-none' : '',
                    sortBy === c.key ? 'text-brand' : '',
                  ].join(' ')}
                  onClick={c.sortable ? () => onSortChange(c.key) : undefined}
                >
                  {c.label} {c.sortable && sortBy === c.key && '↓'}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr>
                <td colSpan={COLS.length} className="py-12 text-center text-gray-400">
                  Loading…
                </td>
              </tr>
            ) : videos.length === 0 ? (
              <tr>
                <td colSpan={COLS.length} className="py-12 text-center text-gray-400">
                  No videos yet. Fetch trending or run a search.
                </td>
              </tr>
            ) : (
              videos.map((v) => (
                <tr key={v.video_id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 max-w-xs">
                    <a
                      href={`https://youtube.com/watch?v=${v.video_id}`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-blue-600 hover:underline line-clamp-2 font-medium"
                    >
                      {v.title ?? v.video_id}
                    </a>
                  </td>
                  <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{v.channel_title ?? '—'}</td>
                  <td className="px-4 py-3 font-mono text-gray-800 whitespace-nowrap">{formatNumber(v.view_count)}</td>
                  <td className="px-4 py-3 font-mono text-gray-600 whitespace-nowrap">{formatNumber(v.like_count)}</td>
                  <td className="px-4 py-3 font-mono text-gray-600 whitespace-nowrap">{formatNumber(v.comment_count)}</td>
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{formatDate(v.published_at)}</td>
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{parseDuration(v.duration)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="px-4 py-3 border-t border-gray-100 flex items-center justify-between text-sm text-gray-500">
        <span>{total} videos total</span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="px-3 py-1 rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
          >
            Prev
          </button>
          <span className="px-2">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="px-3 py-1 rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
