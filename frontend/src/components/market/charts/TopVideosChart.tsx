import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import type { TopVideoItem } from '../../../types/market'
import { formatNumber } from '../../../lib/formatters'

interface Props {
  videos: TopVideoItem[]
}

function truncate(s: string | null, n = 30) {
  if (!s) return 'Unknown'
  return s.length > n ? s.slice(0, n) + '…' : s
}

export function TopVideosChart({ videos }: Props) {
  if (videos.length === 0) return <EmptyState />
  const data = videos.map((v) => ({ name: truncate(v.title), views: v.view_count, likes: v.like_count }))
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} layout="vertical" margin={{ left: 10, right: 30, top: 5, bottom: 5 }}>
        <XAxis type="number" tickFormatter={formatNumber} tick={{ fontSize: 11 }} />
        <YAxis type="category" dataKey="name" width={160} tick={{ fontSize: 11 }} />
        <Tooltip formatter={(v: unknown) => formatNumber(v as number)} />
        <Bar dataKey="views" radius={[0, 4, 4, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={`hsl(${210 + i * 5}, 70%, ${55 + i * 2}%)`} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function EmptyState() {
  return <div className="h-[300px] flex items-center justify-center text-gray-400 text-sm">No data yet</div>
}
