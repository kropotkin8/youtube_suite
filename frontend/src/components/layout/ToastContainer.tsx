import { useEffect } from 'react'
import { useToastStore } from '../../stores/toastStore'
import type { Toast } from '../../stores/toastStore'

function ToastItem({ toast }: { toast: Toast }) {
  const removeToast = useToastStore((s) => s.removeToast)

  useEffect(() => {
    if (toast.status === 'completed' || toast.status === 'info') {
      const t = setTimeout(() => removeToast(toast.id), 4000)
      return () => clearTimeout(t)
    }
  }, [toast.status, toast.id, removeToast])

  const statusIcon = {
    processing: (
      <svg className="w-4 h-4 animate-spin text-blue-500" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
      </svg>
    ),
    completed: (
      <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
      </svg>
    ),
    failed: (
      <svg className="w-4 h-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
      </svg>
    ),
    info: (
      <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01" />
      </svg>
    ),
  }[toast.status]

  const borderColor = {
    processing: 'border-l-blue-400',
    completed: 'border-l-green-400',
    failed: 'border-l-red-400',
    info: 'border-l-gray-400',
  }[toast.status]

  return (
    <div className={`bg-white rounded-lg shadow-lg border border-gray-100 border-l-4 ${borderColor} p-4 w-80`}>
      <div className="flex items-start gap-3">
        <div className="mt-0.5 shrink-0">{statusIcon}</div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-900 truncate">{toast.title}</p>
          {toast.message && (
            <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{toast.message}</p>
          )}
          {toast.status === 'processing' && toast.progress !== undefined && (
            <div className="mt-2 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-400 rounded-full transition-all duration-500"
                style={{ width: `${Math.round(toast.progress * 100)}%` }}
              />
            </div>
          )}
        </div>
        <button
          onClick={() => removeToast(toast.id)}
          className="shrink-0 text-gray-300 hover:text-gray-500 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  )
}

export function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts)
  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-3 pointer-events-none">
      {toasts.map((t) => (
        <div key={t.id} className="pointer-events-auto">
          <ToastItem toast={t} />
        </div>
      ))}
    </div>
  )
}
