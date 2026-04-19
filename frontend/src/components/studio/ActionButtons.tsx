import { useState } from 'react'
import { studioApi } from '../../api/studio'
import type { AssetListItem } from '../../types/studio'

interface Props {
  asset: AssetListItem
  onJobStarted: (jobId: string, label: string) => void
  onRefresh: () => void
}

function Btn({ label, onClick, disabled }: { label: string; onClick: () => void; disabled: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="flex-1 py-2 px-3 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
    >
      {label}
    </button>
  )
}

export function ActionButtons({ asset, onJobStarted, onRefresh: _onRefresh }: Props) {
  const [subOpen, setSubOpen] = useState(false)
  const [subLoading, setSubLoading] = useState(false)
  const [descOpen, setDescOpen] = useState(false)
  const [descLoading, setDescLoading] = useState(false)
  const [descProvider, setDescProvider] = useState<'claude' | 'local'>('local')
  const [shortsOpen, setShortsOpen] = useState(false)
  const [shortsLoading, setShortsLoading] = useState(false)
  const [subLang, setSubLang] = useState('es')
  const [descLang, setDescLang] = useState('es')
  const [shortsLang, setShortsLang] = useState('es')
  const [modelSize, setModelSize] = useState('medium')
  const [shortsVertical, setShortsVertical] = useState(false)
  const [shortsTitles, setShortsTitles] = useState(false)

  async function runSubtitles() {
    setSubLoading(true)
    try {
      const res = await studioApi.runSubtitles(asset.id, {
        model_size: modelSize,
        language: subLang,
        chunk_minutes: 10,
        overlap_seconds: 5,
      })
      onJobStarted(res.job_id, 'Generating subtitles')
      setSubOpen(false)
    } finally {
      setSubLoading(false)
    }
  }

  async function runDescription() {
    setDescLoading(true)
    try {
      const res = await studioApi.runDescription(asset.id, { language: descLang, provider: descProvider })
      onJobStarted(res.job_id, 'Generating description')
      setDescOpen(false)
    } finally {
      setDescLoading(false)
    }
  }

  async function runShorts() {
    setShortsLoading(true)
    try {
      const res = await studioApi.runShorts(asset.id, {
        language: shortsLang,
        generate_vertical: shortsVertical,
        generate_titles: shortsTitles,
      })
      onJobStarted(res.job_id, 'Generating shorts')
      setShortsOpen(false)
    } finally {
      setShortsLoading(false)
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <Btn label="Generate Subtitles" onClick={() => setSubOpen((o) => !o)} disabled={subLoading} />
        <Btn
          label="Generate Description"
          onClick={() => setDescOpen((o) => !o)}
          disabled={descLoading || !asset.has_transcript}
        />
        <Btn
          label="Generate Shorts"
          onClick={() => setShortsOpen((o) => !o)}
          disabled={shortsLoading}
        />
      </div>
      {subOpen && (
        <div className="bg-gray-50 rounded-lg p-3 space-y-3 border border-gray-200">
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">Language</label>
              <select
                value={subLang}
                onChange={(e) => setSubLang(e.target.value)}
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
              >
                <option value="es">Español</option>
                <option value="en">English</option>
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">Model</label>
              <select
                value={modelSize}
                onChange={(e) => setModelSize(e.target.value)}
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
              >
                {['small', 'medium', 'large-v2'].map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
          </div>
          <button
            onClick={runSubtitles}
            disabled={subLoading}
            className="w-full py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {subLoading ? 'Starting…' : 'Start'}
          </button>
        </div>
      )}
      {descOpen && (
        <div className="bg-gray-50 rounded-lg p-3 space-y-3 border border-gray-200">
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">Language</label>
              <select
                value={descLang}
                onChange={(e) => setDescLang(e.target.value)}
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
              >
                <option value="es">Español</option>
                <option value="en">English</option>
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">Provider</label>
              <select
                value={descProvider}
                onChange={(e) => setDescProvider(e.target.value as 'claude' | 'local')}
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
              >
                <option value="local">Local (Mistral / Ollama)</option>
                <option value="claude">Claude (Anthropic API)</option>
              </select>
            </div>
          </div>
          <button
            onClick={runDescription}
            disabled={descLoading}
            className="w-full py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {descLoading ? 'Starting…' : 'Start'}
          </button>
        </div>
      )}
      {shortsOpen && (
        <div className="bg-gray-50 rounded-lg p-3 space-y-3 border border-gray-200">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Language</label>
            <select
              value={shortsLang}
              onChange={(e) => setShortsLang(e.target.value)}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
            >
              <option value="es">Español</option>
              <option value="en">English</option>
              <option value="fr">Français</option>
              <option value="de">Deutsch</option>
              <option value="pt">Português</option>
            </select>
          </div>
          <div className="flex gap-4">
            <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer">
              <input
                type="checkbox"
                checked={shortsVertical}
                onChange={(e) => setShortsVertical(e.target.checked)}
                className="rounded"
              />
              9:16 vertical clips
            </label>
            <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer">
              <input
                type="checkbox"
                checked={shortsTitles}
                onChange={(e) => setShortsTitles(e.target.checked)}
                className="rounded"
              />
              AI titles (Claude)
            </label>
          </div>
          <button
            onClick={runShorts}
            disabled={shortsLoading}
            className="w-full py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {shortsLoading ? 'Starting…' : 'Start'}
          </button>
        </div>
      )}
      {!asset.has_transcript && (
        <p className="text-xs text-gray-400">Generate subtitles first to enable Description.</p>
      )}
    </div>
  )
}
