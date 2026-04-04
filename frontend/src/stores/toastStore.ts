import { create } from 'zustand'

export interface Toast {
  id: string
  title: string
  message?: string
  status: 'processing' | 'completed' | 'failed' | 'info'
  progress?: number
}

interface ToastStore {
  toasts: Toast[]
  addToast: (t: Toast) => void
  updateToast: (id: string, patch: Partial<Toast>) => void
  removeToast: (id: string) => void
}

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (t) => set((s) => ({ toasts: [...s.toasts, t] })),
  updateToast: (id, patch) =>
    set((s) => ({
      toasts: s.toasts.map((t) => (t.id === id ? { ...t, ...patch } : t)),
    })),
  removeToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}))
