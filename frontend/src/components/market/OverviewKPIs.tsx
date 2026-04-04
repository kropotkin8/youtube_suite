import type { MarketOverview } from '../../types/market'
import { formatNumber } from '../../lib/formatters'

interface Props {
  overview: MarketOverview | null
  loading: boolean
}

const CARDS = [
  { key: 'total_videos' as const, label: 'Videos', color: 'bg-blue-50 text-blue-700', icon: '🎬' },
  { key: 'total_channels' as const, label: 'Channels', color: 'bg-purple-50 text-purple-700', icon: '📺' },
  { key: 'total_views' as const, label: 'Total Views', color: 'bg-green-50 text-green-700', icon: '👁️' },
  { key: 'total_comments' as const, label: 'Comments', color: 'bg-orange-50 text-orange-700', icon: '💬' },
]

export function OverviewKPIs({ overview, loading }: Props) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {CARDS.map(({ key, label, color, icon }) => (
        <div key={key} className={`rounded-xl p-5 ${color}`}>
          <div className="text-2xl mb-1">{icon}</div>
          <div className="text-2xl font-bold">
            {loading || !overview ? '—' : formatNumber(overview[key])}
          </div>
          <div className="text-sm font-medium opacity-75 mt-0.5">{label}</div>
        </div>
      ))}
    </div>
  )
}
