import type { AssetListItem } from '../../types/studio'
import { AssetListItemRow } from './AssetListItem'

interface Props {
  assets: AssetListItem[]
  selectedId: string | null
  onSelect: (id: string) => void
}

export function AssetList({ assets, selectedId, onSelect }: Props) {
  if (assets.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400 text-sm">
        No assets yet.<br />Upload a video above.
      </div>
    )
  }
  return (
    <div className="space-y-1">
      {assets.map((a) => (
        <AssetListItemRow
          key={a.id}
          asset={a}
          selected={selectedId === a.id}
          onSelect={() => onSelect(a.id)}
        />
      ))}
    </div>
  )
}
