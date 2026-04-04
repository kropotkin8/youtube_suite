import { useCallback } from 'react'
import { useJobPoller } from '../../hooks/useJobPoller'
import { useToastStore } from '../../stores/toastStore'
import type { JobStatus } from '../../types/studio'

interface Props {
  jobId: string
  label: string
  onDone: () => void
}

export function JobWatcher({ jobId, label, onDone }: Props) {
  const { addToast, updateToast } = useToastStore()

  const handleUpdate = useCallback((status: JobStatus) => {
    updateToast(jobId, {
      status: 'processing',
      progress: status.progress,
      message: status.message ?? undefined,
    })
  }, [jobId, updateToast])

  const handleDone = useCallback((status: JobStatus) => {
    if (status.status === 'completed') {
      updateToast(jobId, { status: 'completed', progress: 1, message: 'Done' })
    } else {
      updateToast(jobId, { status: 'failed', message: status.error ?? 'Failed' })
    }
    onDone()
  }, [jobId, updateToast, onDone])

  const handleError = useCallback((err: Error) => {
    updateToast(jobId, { status: 'failed', message: err.message })
    onDone()
  }, [jobId, updateToast, onDone])

  // Register toast on first render
  const addToastOnce = useCallback(() => {
    addToast({ id: jobId, title: label, status: 'processing', progress: 0 })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // We need to add toast before polling starts; use a ref trick
  const toasts = useToastStore((s) => s.toasts)
  if (!toasts.find((t) => t.id === jobId)) {
    addToastOnce()
  }

  useJobPoller({ jobId, onUpdate: handleUpdate, onDone: handleDone, onError: handleError })

  return null
}
