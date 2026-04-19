import { get, post } from './client'
import type {
  Asset,
  AssetListResponse,
  Description,
  JobStartResult,
  ShortsResult,
  Transcript,
} from '../types/studio'

export const studioApi = {
  listAssets: () => get<AssetListResponse>('/studio/assets'),

  getAsset: (id: string) => get<Asset>(`/studio/assets/${id}`),

  getTranscript: (id: string) => get<Transcript>(`/studio/assets/${id}/transcript`),

  getDescription: (id: string) => get<Description>(`/studio/assets/${id}/description`),

  getShorts: (id: string) => get<ShortsResult>(`/studio/assets/${id}/shorts`),

  runSubtitles: (
    id: string,
    body: { model_size: string; language: string; chunk_minutes: number; overlap_seconds: number }
  ) => post<JobStartResult>(`/studio/assets/${id}/subtitles/run`, body),

  runDescription: (id: string, body: { language: string; provider: 'claude' | 'local' }) =>
    post<JobStartResult>(`/studio/assets/${id}/description/run`, body),

  runShorts: (id: string, body: { language: string; generate_vertical?: boolean; generate_titles?: boolean }) =>
    post<JobStartResult>(`/studio/assets/${id}/shorts/run`, body),

  rescoreShorts: (id: string, weights: Record<string, number>) =>
    post<ShortsResult>(`/studio/assets/${id}/shorts/rescore`, { weights }),

  generateClipTitle: (assetId: string, clipId: string) =>
    post<{ clip_id: string; title: string; hashtags: string[] }>(`/studio/assets/${assetId}/clips/${clipId}/title`, {}),

  videoUrl: (id: string) => `/studio/assets/${id}/video`,
  subtitledVideoUrl: (id: string) => `/studio/assets/${id}/video/subtitled`,

  uploadAsset: (
    file: File,
    onProgress: (pct: number) => void
  ): Promise<{ asset_id: string; filename: string }> =>
    new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.open('POST', '/studio/assets/upload')
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100))
      }
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText))
        } else {
          try {
            const detail = JSON.parse(xhr.responseText)?.detail
            reject(new Error(detail ?? `Upload failed: ${xhr.status}`))
          } catch {
            reject(new Error(`Upload failed: ${xhr.status}`))
          }
        }
      }
      xhr.onerror = () => reject(new Error('Network error'))
      const fd = new FormData()
      fd.append('file', file)
      xhr.send(fd)
    }),
}
