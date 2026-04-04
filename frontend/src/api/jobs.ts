import { get } from './client'
import type { JobStatus } from '../types/studio'

export const jobsApi = {
  getStatus: (jobId: string) => get<JobStatus>(`/jobs/${jobId}`),
  clipVideoUrl: (jobId: string, clipId: string) => `/jobs/${jobId}/clips/${clipId}`,
}
