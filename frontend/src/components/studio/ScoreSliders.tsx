import { useState } from 'react'

interface Weights {
  shortability: number
  semantic: number
  hook: number
  speaker_change: number
}

interface Props {
  onRescore: (weights: Weights) => Promise<void>
  loading: boolean
}

const LABELS: Record<keyof Weights, string> = {
  shortability: 'Shortability (AI model)',
  semantic: 'Semantic relevance',
  hook: 'Hook strength',
  speaker_change: 'Speaker dynamics',
}

const DEFAULTS: Weights = { shortability: 0.5, semantic: 0.2, hook: 0.15, speaker_change: 0.15 }

function normalize(w: Weights): Weights {
  const total = Object.values(w).reduce((a, b) => a + b, 0)
  if (total === 0) return DEFAULTS
  return Object.fromEntries(
    Object.entries(w).map(([k, v]) => [k, v / total])
  ) as Weights
}

export function ScoreSliders({ onRescore, loading }: Props) {
  const [open, setOpen] = useState(false)
  const [weights, setWeights] = useState<Weights>({ ...DEFAULTS })

  function setWeight(key: keyof Weights, val: number) {
    setWeights((prev) => ({ ...prev, [key]: val }))
  }

  async function handleRescore() {
    await onRescore(normalize(weights))
  }

  return (
    <div className="border-t border-gray-100 pt-4">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 font-medium"
      >
        <svg className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
        Adjust scoring weights
      </button>
      {open && (
        <div className="mt-3 space-y-3">
          {(Object.keys(LABELS) as (keyof Weights)[]).map((key) => (
            <div key={key}>
              <div className="flex justify-between text-xs text-gray-600 mb-1">
                <span>{LABELS[key]}</span>
                <span className="font-mono">{weights[key].toFixed(2)}</span>
              </div>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={weights[key]}
                onChange={(e) => setWeight(key, parseFloat(e.target.value))}
                className="w-full h-1.5 accent-blue-600"
              />
            </div>
          ))}
          <button
            onClick={handleRescore}
            disabled={loading}
            className="w-full py-1.5 rounded-lg bg-blue-600 text-white text-xs font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Rescoring…' : 'Rescore clips'}
          </button>
          <p className="text-xs text-gray-400 text-center">Weights are normalised automatically</p>
        </div>
      )}
    </div>
  )
}
