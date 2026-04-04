import { useEffect, useRef, useCallback } from 'react'
import { jobsApi } from '../api/jobs'
import type { JobStatus } from '../types/studio'

interface PollOptions {
  jobId: string
  intervalMs?: number
  onUpdate: (status: JobStatus) => void
  onDone: (status: JobStatus) => void
  onError: (error: Error) => void
}

export function useJobPoller({
  jobId,
  intervalMs = 2000,
  onUpdate,
  onDone,
  onError,
}: PollOptions): void {
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const poll = useCallback(async () => {
    try {
      const status = await jobsApi.getStatus(jobId)
      onUpdate(status)
      if (status.status === 'completed' || status.status === 'failed') {
        if (timerRef.current) clearInterval(timerRef.current)
        onDone(status)
      }
    } catch (err) {
      if (timerRef.current) clearInterval(timerRef.current)
      onError(err as Error)
    }
  }, [jobId, onUpdate, onDone, onError])

  useEffect(() => {
    poll()
    timerRef.current = setInterval(poll, intervalMs)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [poll, intervalMs])
}
