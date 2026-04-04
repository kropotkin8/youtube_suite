import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import type { CategoryBreakdownItem } from '../../../types/market'
import { formatNumber } from '../../../lib/formatters'

interface Props {
  data: CategoryBreakdownItem[]
}

const COLORS = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#f97316','#84cc16','#ec4899','#6366f1']

const CATEGORY_NAMES: Record<string, string> = {
  '1':'Film','2':'Autos','10':'Music','15':'Pets','17':'Sports',
  '19':'Travel','20':'Gaming','22':'People','23':'Comedy','24':'Entertainment',
  '25':'News','26':'How-to','27':'Education','28':'Science','29':'Nonprofits',
}

function label(id: string | null) {
  if (!id) return 'Other'
  return CATEGORY_NAMES[id] ?? `Cat ${id}`
}

export function CategoryPieChart({ data }: Props) {
  if (data.length === 0) return <EmptyState />
  const chartData = data.slice(0, 10).map((d) => ({ name: label(d.category_id), value: d.count, views: d.total_views }))
  return (
    <ResponsiveContainer width="100%" height={250}>
      <PieChart>
        <Pie
          data={chartData}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={90}
          label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
          labelLine={false}
        >
          {chartData.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip formatter={(v: unknown, _name: unknown, props: { payload?: { views?: number } }) => [formatNumber(v as number), `Videos (${formatNumber((props?.payload?.views ?? 0))} views)`]} />
      </PieChart>
    </ResponsiveContainer>
  )
}

function EmptyState() {
  return <div className="h-[250px] flex items-center justify-center text-gray-400 text-sm">No data yet</div>
}
