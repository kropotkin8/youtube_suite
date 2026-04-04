import type { AssetListItem } from '../../types/studio'

interface Props {
  asset: AssetListItem
  selected: boolean
  onSelect: () => void
}

function Dot({ active, title }: { active: boolean; title: string }) {
  return (
    <span
      title={title}
      className={[
        'inline-block w-2 h-2 rounded-full',
        active ? 'bg-green-400' : 'bg-gray-200',
      ].join(' ')}
    />
  )
}

export function AssetListItemRow({ asset, selected, onSelect }: Props) {
  return (
    <button
      onClick={onSelect}
      className={[
        'w-full text-left px-3 py-3 rounded-lg transition-colors',
        selected ? 'bg-blue-50 border border-blue-200' : 'hover:bg-gray-50',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-gray-900 line-clamp-2 leading-snug">
          {asset.title || asset.filename}
        </p>
        <div className="flex gap-1 mt-0.5 shrink-0">
          <Dot active={asset.has_transcript} title="Subtitles" />
          <Dot active={asset.has_description} title="Description" />
          <Dot active={asset.has_shorts} title="Shorts" />
        </div>
      </div>
      <p className="text-xs text-gray-400 mt-1 truncate">{asset.filename}</p>
    </button>
  )
}
