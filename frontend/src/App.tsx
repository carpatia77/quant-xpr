import { useEffect, useState, useRef, useCallback } from 'react'
import Q1Signal from './components/Q1Signal'
import Q2Smile from './components/Q2Smile'
import Q3History from './components/Q3History'
import Q4Table from './components/Q4Table'
import TickerTape, { TickerData } from './components/TickerTape'
import DataSources from './components/DataSources'

let API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
if (API_BASE.endsWith('/')) {
  API_BASE = API_BASE.slice(0, -1);
}
const API_KEY = import.meta.env.VITE_API_KEY || 'quant-secret-key';

type Tab = 'dashboard' | 'datasources'

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard')
  const [data, setData] = useState<any>(null)
  const [history, setHistory] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const [tapeData, setTapeData] = useState<TickerData[]>([])
  const [newTicker, setNewTicker] = useState('')
  const [isAdding, setIsAdding] = useState(false)

  const [selectedTicker, setSelectedTicker] = useState<string>(() => {
    const params = new URLSearchParams(window.location.search)
    return params.get('ticker') || 'PETR4.SA'
  })

  const [customRfr, setCustomRfr] = useState<number | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const fetchSummary = useCallback(async (ticker: string, rfrOverride: number | null = null) => {
    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setLoading(true)
    setErrorMsg(null)
    try {
      let url = `${API_BASE}/v1/summary/${ticker}`
      if (rfrOverride !== null) url += `?rfr=${rfrOverride / 100}`
      const res = await fetch(url, {
        headers: { 'X-API-Key': API_KEY },
        signal: controller.signal,
      })
      if (res.ok) {
        setData(await res.json())
      } else {
        setErrorMsg(`API Error: ${res.status} ${res.statusText}`)
      }
      const histRes = await fetch(`${API_BASE}/v1/history/${ticker}?limit=10`, {
        headers: { 'X-API-Key': API_KEY },
        signal: controller.signal,
      })
      if (histRes.ok) setHistory(await histRes.json())
    } catch (e: any) {
      if (e.name === 'AbortError') return
      setErrorMsg(e.message || 'Network connection failed')
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    params.set('ticker', selectedTicker)
    window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`)
    fetchSummary(selectedTicker, customRfr)
  }, [selectedTicker, customRfr, fetchSummary])

  const fetchWatchlist = async () => {
    try {
      const res = await fetch(`${API_BASE}/v1/watchlist/summary`, { headers: { 'X-API-Key': API_KEY } })
      if (res.ok) setTapeData(await res.json())
    } catch {}
  }

  const handleAddTicker = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTicker.trim()) return
    setIsAdding(true)
    try {
      await fetch(`${API_BASE}/v1/watchlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
        body: JSON.stringify({ ticker: newTicker.trim().toUpperCase() }),
      })
      setNewTicker('')
      await fetchWatchlist()
    } catch {}
    setIsAdding(false)
  }

  const handleRemoveTicker = async (ticker: string) => {
    try {
      await fetch(`${API_BASE}/v1/watchlist/${ticker}`, { method: 'DELETE', headers: { 'X-API-Key': API_KEY } })
      await fetchWatchlist()
    } catch {}
  }

  const handleTickerClick = (ticker: string) => {
    if (ticker === selectedTicker) return
    setCustomRfr(null)
    setSelectedTicker(ticker)
    setActiveTab('dashboard') // volta ao dashboard ao clicar no tape
  }

  useEffect(() => {
    fetchWatchlist()
    const interval = setInterval(fetchWatchlist, 10000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="h-screen w-screen bg-background flex flex-col overflow-hidden">
      <TickerTape items={tapeData} onRemove={handleRemoveTicker} onClickTicker={handleTickerClick} />

      <div className="flex-1 flex flex-col p-2 min-h-0">
        {/* Header */}
        <header className="flex items-center justify-between border-b border-border pb-2 mb-2 shrink-0">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-accent tracking-widest px-2">QUANT_XPR</h1>

            {/* Tab switcher */}
            <div className="flex">
              <button
                onClick={() => setActiveTab('dashboard')}
                className={`px-3 py-1 text-xs font-bold tracking-widest border transition-colors ${
                  activeTab === 'dashboard'
                    ? 'bg-accent text-background border-accent'
                    : 'bg-panel border-border text-muted-foreground hover:border-accent hover:text-accent'
                }`}
              >
                DASHBOARD
              </button>
              <button
                onClick={() => setActiveTab('datasources')}
                className={`px-3 py-1 text-xs font-bold tracking-widest border-t border-b border-r transition-colors ${
                  activeTab === 'datasources'
                    ? 'bg-accent text-background border-accent'
                    : 'bg-panel border-border text-muted-foreground hover:border-accent hover:text-accent'
                }`}
              >
                DATA SOURCES
              </button>
            </div>

            {activeTab === 'dashboard' && (
              <>
                <span className="text-xs bg-panel px-2 py-1 border border-border text-muted-foreground font-bold tracking-widest flex items-center gap-2">
                  {data ? (
                    <>
                      <span>{data.ticker}</span>
                      {data.company_name && data.company_name !== data.ticker && (
                        <span className="text-foreground/50">| {data.company_name.substring(0, 20)}</span>
                      )}
                      {data.spot_price > 0 && (
                        <span className="text-foreground">| R$ {data.spot_price.toFixed(2)}</span>
                      )}
                      {data.change_percent !== undefined && data.change_percent !== 0 && (
                        <span className={data.change_percent >= 0 ? 'text-bull' : 'text-bear'}>
                          {data.change_percent >= 0 ? '+' : ''}{data.change_percent.toFixed(2)}%
                        </span>
                      )}
                    </>
                  ) : 'LOADING'}
                </span>
                <form onSubmit={handleAddTicker} className="flex items-center">
                  <input
                    type="text"
                    placeholder="Add to Watchlist..."
                    value={newTicker}
                    onChange={e => setNewTicker(e.target.value)}
                    className="bg-panel border border-border px-2 py-1 text-xs text-foreground focus:outline-none focus:border-accent w-40"
                  />
                  <button
                    type="submit"
                    disabled={isAdding}
                    className="bg-accent text-background px-3 py-1 text-xs font-bold hover:bg-accent/80 transition-colors disabled:opacity-50"
                  >
                    ADD
                  </button>
                </form>
              </>
            )}
          </div>
          <div className="text-xs font-bold tracking-widest text-bull px-4 animate-pulse">
            MARKET DATA CONNECTED
          </div>
        </header>

        {/* Content area */}
        {activeTab === 'datasources' ? (
          <div className="flex-1 bg-panel border border-border p-4 overflow-hidden">
            <DataSources apiBase={API_BASE} apiKey={API_KEY} />
          </div>
        ) : loading ? (
          <div className="flex-1 flex items-center justify-center text-accent animate-pulse font-bold tracking-widest">
            INITIALIZING QUADRANTS...
          </div>
        ) : errorMsg ? (
          <div className="flex-1 flex items-center justify-center text-bear font-bold tracking-widest">
            SYSTEM ERROR: {errorMsg}
          </div>
        ) : (
          <div className="flex-1 grid grid-cols-2 grid-rows-2 gap-2 min-h-0">
            <div className="bg-panel border border-border p-4 overflow-hidden">
              <Q1Signal data={data} onOverrideRfr={(val) => setCustomRfr(val)} />
            </div>
            <div className="bg-panel border border-border p-4 overflow-hidden">
              <Q2Smile data={data} />
            </div>
            <div className="bg-panel border border-border p-0 overflow-hidden">
              <Q3History data={data} />
            </div>
            <div className="bg-panel border border-border p-4 overflow-hidden flex flex-col">
              <Q4Table historyData={history} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
