import { get, post } from './client'
import type {
  CategoryBreakdownResponse,
  MarketOverview,
  MarketVideoListResponse,
  SyncResult,
  TopVideosResponse,
  ViewsOverTimeResponse,
} from '../types/market'

export const marketApi = {
  getOverview: () => get<MarketOverview>('/market/overview'),

  listVideos: (page = 1, limit = 25, sort_by = 'view_count') =>
    get<MarketVideoListResponse>(
      `/market/videos?page=${page}&limit=${limit}&sort_by=${sort_by}`
    ),

  syncTrending: (body: { region: string; limit: number; max_comment_pages: number }) =>
    post<SyncResult>('/market/sync/trending', body),

  syncSearch: (body: {
    query: string
    limit: number
    region?: string
    max_comment_pages?: number
  }) => post<SyncResult>('/market/sync/search', body),

  getTopVideos: (limit = 10) =>
    get<TopVideosResponse>(`/market/charts/top-videos?limit=${limit}`),

  getViewsOverTime: (days = 30) =>
    get<ViewsOverTimeResponse>(`/market/charts/views-over-time?days=${days}`),

  getCategoryBreakdown: () =>
    get<CategoryBreakdownResponse>('/market/charts/category-breakdown'),
}
