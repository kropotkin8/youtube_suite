import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import type { ViewsOverTimePoint } from '../../../types/market'
import { formatNumber } from '../../../lib/formatters'

interface Props {
  data: ViewsOverTimePoint[]
}

export function ViewsOverTimeChart({ data }: Props) {
  if (data.length === 0) return <EmptyState />
  return (
    <ResponsiveContainer width="100%" height={250}>
      <AreaChart data={data} margin={{ left: 10, right: 10, top: 5, bottom: 5 }}>
        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
        <YAxis tickFormatter={formatNumber} tick={{ fontSize: 11 }} width={55} />
        <Tooltip formatter={(v: unknown) => formatNumber(v as number)} />
        <Legend />
        <Area
          type="monotone"
          dataKey="total_views"
          name="Views"
          stroke="#3b82f6"
          fill="#bfdbfe"
          strokeWidth={2}
        />
        <Area
          type="monotone"
          dataKey="total_likes"
          name="Likes"
          stroke="#10b981"
          fill="#a7f3d0"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}

function EmptyState() {
  return <div className="h-[250px] flex items-center justify-center text-gray-400 text-sm">No data yet</div>
}
