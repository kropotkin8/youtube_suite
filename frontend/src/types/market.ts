export interface MarketOverview {
  total_videos: number
  total_channels: number
  total_comments: number
  total_views: number
}

export interface MarketVideoListItem {
  video_id: string
  title: string | null
  channel_title: string | null
  view_count: number
  like_count: number
  comment_count: number
  published_at: string | null
  duration: string | null
  category_id: string | null
}

export interface MarketVideoListResponse {
  total: number
  page: number
  limit: number
  videos: MarketVideoListItem[]
}

export interface TopVideoItem {
  video_id: string
  title: string | null
  view_count: number
  like_count: number
  comment_count: number
}

export interface TopVideosResponse {
  videos: TopVideoItem[]
}

export interface ViewsOverTimePoint {
  date: string
  total_views: number
  total_likes: number
}

export interface ViewsOverTimeResponse {
  data: ViewsOverTimePoint[]
}

export interface CategoryBreakdownItem {
  category_id: string | null
  count: number
  total_views: number
}

export interface CategoryBreakdownResponse {
  data: CategoryBreakdownItem[]
}

export interface SyncResult {
  [key: string]: number
}
