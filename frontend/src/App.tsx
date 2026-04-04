import { useState } from 'react'
import { TabBar } from './components/layout/TabBar'
import { ToastContainer } from './components/layout/ToastContainer'
import { MarketTab } from './components/market/MarketTab'
import { StudioTab } from './components/studio/StudioTab'

function App() {
  const [tab, setTab] = useState<'market' | 'studio'>('market')

  return (
    <div className="min-h-screen bg-gray-50">
      <TabBar active={tab} onChange={setTab} />
      <main>
        {tab === 'market' ? <MarketTab /> : <StudioTab />}
      </main>
      <ToastContainer />
    </div>
  )
}

export default App
