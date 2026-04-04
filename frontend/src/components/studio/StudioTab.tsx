import { useState, useEffect, useCallback } from 'react'
import { studioApi } from '../../api/studio'
import type { AssetListItem } from '../../types/studio'
import { DropZone } from './DropZone'
import { AssetList } from './AssetList'
import { AssetDetail } from './AssetDetail'

export function StudioTab() {
  const [assets, setAssets] = useState<AssetListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const fetchAssets = useCallback(async () => {
    try {
      const data = await studioApi.listAssets()
      setAssets(data.assets)
      // Auto-select first if none selected
      setSelectedId((prev) => prev ?? data.assets[0]?.id ?? null)
    } catch {
      /* ignore */
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAssets()
  }, [fetchAssets])

  const selectedAsset = assets.find((a) => a.id === selectedId) ?? null

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Studio</h1>
        <span className="text-sm text-gray-400">{assets.length} asset{assets.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Upload */}
      <DropZone onUploaded={fetchAssets} />

      {/* Main two-panel layout */}
      <div className="flex gap-4 min-h-[600px]">
        {/* Left: asset list */}
        <div className="w-72 shrink-0 bg-white rounded-xl border border-gray-200 p-3 overflow-y-auto">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Assets</p>
            <div className="flex gap-1" title="Subtitles / Description / Shorts">
              <span className="w-2 h-2 rounded-full bg-green-400" />
              <span className="w-2 h-2 rounded-full bg-green-400" />
              <span className="w-2 h-2 rounded-full bg-green-400" />
            </div>
          </div>
          {loading ? (
            <p className="text-sm text-gray-400 text-center py-6">Loading…</p>
          ) : (
            <AssetList assets={assets} selectedId={selectedId} onSelect={setSelectedId} />
          )}
        </div>

        {/* Right: detail panel */}
        <div className="flex-1 bg-white rounded-xl border border-gray-200 p-5">
          {selectedAsset ? (
            <AssetDetail asset={selectedAsset} onRefresh={fetchAssets} />
          ) : (
            <div className="h-full flex items-center justify-center text-gray-400 text-sm">
              Select an asset to view details
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
