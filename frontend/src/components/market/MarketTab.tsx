import { useState, useEffect, useCallback } from 'react'
import { marketApi } from '../../api/market'
import { useToastStore } from '../../stores/toastStore'
import type { MarketOverview, MarketVideoListItem } from '../../types/market'
import type { TopVideoItem, ViewsOverTimePoint, CategoryBreakdownItem } from '../../types/market'
import { OverviewKPIs } from './OverviewKPIs'
import { VideoTable } from './VideoTable'
import { SearchModal } from './SearchModal'
import { TrendingButton } from './TrendingButton'
import { TopVideosChart } from './charts/TopVideosChart'
import { ViewsOverTimeChart } from './charts/ViewsOverTimeChart'
import { CategoryPieChart } from './charts/CategoryPieChart'

export function MarketTab() {
  const { addToast } = useToastStore()

  const [overview, setOverview] = useState<MarketOverview | null>(null)
  const [overviewLoading, setOverviewLoading] = useState(true)

  const [videos, setVideos] = useState<MarketVideoListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [sortBy, setSortBy] = useState('view_count')
  const [tableLoading, setTableLoading] = useState(true)

  const [topVideos, setTopVideos] = useState<TopVideoItem[]>([])
  const [viewsOverTime, setViewsOverTime] = useState<ViewsOverTimePoint[]>([])
  const [categories, setCategories] = useState<CategoryBreakdownItem[]>([])

  const [searchOpen, setSearchOpen] = useState(false)

  const fetchOverview = useCallback(async () => {
    setOverviewLoading(true)
    try {
      const data = await marketApi.getOverview()
      setOverview(data)
    } catch {
      /* ignore */
    } finally {
      setOverviewLoading(false)
    }
  }, [])

  const fetchVideos = useCallback(async (p: number, sort: string) => {
    setTableLoading(true)
    try {
      const data = await marketApi.listVideos(p, 25, sort)
      setVideos(data.videos)
      setTotal(data.total)
    } catch {
      /* ignore */
    } finally {
      setTableLoading(false)
    }
  }, [])

  const fetchCharts = useCallback(async () => {
    try {
      const [tv, vot, cb] = await Promise.all([
        marketApi.getTopVideos(10),
        marketApi.getViewsOverTime(30),
        marketApi.getCategoryBreakdown(),
      ])
      setTopVideos(tv.videos)
      setViewsOverTime(vot.data)
      setCategories(cb.data)
    } catch {
      /* ignore */
    }
  }, [])

  useEffect(() => {
    fetchOverview()
    fetchCharts()
  }, [fetchOverview, fetchCharts])

  useEffect(() => {
    fetchVideos(page, sortBy)
  }, [page, sortBy, fetchVideos])

  function handleSortChange(col: string) {
    setSortBy(col)
    setPage(1)
  }

  async function handleSyncTrending() {
    await marketApi.syncTrending({ region: 'ES', limit: 50, max_comment_pages: 3 })
    addToast({ id: `trending-${Date.now()}`, title: 'Trending sync complete', status: 'completed' })
    fetchOverview()
    fetchVideos(1, sortBy)
    fetchCharts()
    setPage(1)
  }

  async function handleSearch(query: string, limit: number, region: string) {
    addToast({ id: `search-${Date.now()}`, title: `Searching "${query}"…`, status: 'processing' })
    await marketApi.syncSearch({ query, limit, region, max_comment_pages: 3 })
    addToast({ id: `search-done-${Date.now()}`, title: `Search "${query}" imported`, status: 'completed' })
    fetchOverview()
    fetchVideos(1, sortBy)
    fetchCharts()
    setPage(1)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-bold text-gray-900">Market Intelligence</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSearchOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 105 11a6 6 0 0012 0z" />
            </svg>
            Search
          </button>
          <TrendingButton onSync={handleSyncTrending} />
        </div>
      </div>

      {/* KPIs */}
      <OverviewKPIs overview={overview} loading={overviewLoading} />

      {/* Table */}
      <VideoTable
        videos={videos}
        total={total}
        page={page}
        limit={25}
        sortBy={sortBy}
        loading={tableLoading}
        onPageChange={setPage}
        onSortChange={handleSortChange}
      />

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Top 10 Videos by Views</h2>
          <TopVideosChart videos={topVideos} />
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Videos by Category</h2>
          <CategoryPieChart data={categories} />
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5 lg:col-span-2">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Views & Likes Over Time (30d)</h2>
          <ViewsOverTimeChart data={viewsOverTime} />
        </div>
      </div>

      <SearchModal
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        onSubmit={handleSearch}
      />
    </div>
  )
}
