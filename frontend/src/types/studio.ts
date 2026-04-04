export interface AssetListItem {
  id: string
  filename: string
  title: string | null
  duration_seconds: number | null
  market_video_id: string | null
  created_at: string
  has_transcript: boolean
  has_description: boolean
  has_shorts: boolean
}

export interface AssetListResponse {
  total: number
  assets: AssetListItem[]
}

export interface Asset {
  id: string
  filename: string
  title: string | null
  market_video_id: string | null
  storage_key: string
}

export interface TranscriptSegment {
  start: number
  end: number
  text: string
}

export interface Transcript {
  segments: TranscriptSegment[]
}

export interface Description {
  body: string
  model: string | null
}

export interface Clip {
  clip_id: string
  start: number
  end: number
  duration: number
  text: string
  speaker: string | null
  score: number
  path: string
  filename: string
}

export interface ShortsResult {
  job_id: string
  total_clips: number
  clips: Clip[]
}

export interface JobStartResult {
  job_id: string
  message: string
  asset_id?: string
}

export interface JobStatus {
  job_id: string
  status: 'uploaded' | 'processing' | 'completed' | 'failed'
  progress: number
  message: string | null
  error: string | null
}
