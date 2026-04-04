interface TabBarProps {
  active: 'market' | 'studio'
  onChange: (tab: 'market' | 'studio') => void
}

export function TabBar({ active, onChange }: TabBarProps) {
  const tabs = [
    { id: 'market' as const, label: 'Market' },
    { id: 'studio' as const, label: 'Studio' },
  ]
  return (
    <nav className="bg-white border-b border-gray-200 px-6 flex items-center gap-0 shadow-sm">
      <div className="flex items-center gap-3 mr-8">
        <div className="w-6 h-6 bg-brand rounded-full flex items-center justify-center">
          <svg viewBox="0 0 24 24" className="w-4 h-4 fill-white">
            <path d="M10 15l5.19-3L10 9v6zm11.56-7.83..." />
          </svg>
        </div>
        <span className="font-bold text-gray-900 text-lg tracking-tight">CIP</span>
      </div>
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={[
            'px-5 py-4 text-sm font-medium border-b-2 transition-colors',
            active === t.id
              ? 'border-brand text-brand'
              : 'border-transparent text-gray-500 hover:text-gray-800 hover:border-gray-300',
          ].join(' ')}
        >
          {t.label}
        </button>
      ))}
    </nav>
  )
}
