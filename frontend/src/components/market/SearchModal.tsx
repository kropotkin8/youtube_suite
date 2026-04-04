import { useState } from 'react'

interface Props {
  open: boolean
  onClose: () => void
  onSubmit: (query: string, limit: number, region: string) => Promise<void>
}

export function SearchModal({ open, onClose, onSubmit }: Props) {
  const [query, setQuery] = useState('')
  const [limit, setLimit] = useState(25)
  const [region, setRegion] = useState('ES')
  const [loading, setLoading] = useState(false)

  if (!open) return null

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    try {
      await onSubmit(query.trim(), limit, region)
      setQuery('')
      onClose()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-40" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-bold text-gray-900 mb-4">Search YouTube</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Query</label>
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. python tutorials"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand"
            />
          </div>
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Results</label>
              <select
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              >
                {[10, 25, 50].map((n) => (
                  <option key={n} value={n}>{n} videos</option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Region</label>
              <input
                value={region}
                onChange={(e) => setRegion(e.target.value.toUpperCase())}
                maxLength={2}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm uppercase"
              />
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="flex-1 py-2 rounded-lg bg-brand text-white text-sm font-medium hover:bg-brand-dark disabled:opacity-50"
            >
              {loading ? 'Searching…' : 'Search & Import'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
