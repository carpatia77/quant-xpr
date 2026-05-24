import { useEffect, useState } from 'react'
import Q1Signal from './components/Q1Signal'
import Q2Smile from './components/Q2Smile'
import Q3History from './components/Q3History'
import Q4Table from './components/Q4Table'
import TickerTape, { TickerData } from './components/TickerTape'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || 'quant-secret-key';



function App() {
  const [data, setData] = useState<any>(null)
  const [history, setHistory] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const [selectedTicker, setSelectedTicker] = useState<string>(() => {
    const params = new URLSearchParams(window.location.search)
    return params.get('ticker') || 'PETR4.SA'
  })

  const fetchSummary = async (ticker: string) => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/v1/summary/${ticker}`, {
        headers: { 'X-API-Key': API_KEY }
      })
      if (res.ok) {
        const json = await res.json()
        setData(json)
      }
      
      const historyRes = await fetch(`${API_BASE}/v1/history/${ticker}?limit=10`, {
        headers: { 'X-API-Key': API_KEY }
      })
      if (historyRes.ok) {
        const historyJson = await historyRes.json()
        setHistory(historyJson)
      }
    } catch (e) {
      console.error("Failed to fetch summary for", ticker, e)
    }
    setLoading(false)
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    params.set('ticker', selectedTicker)
    window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`)
    fetchSummary(selectedTicker)
  }, [selectedTicker])

  const fetchWatchlist = async () => {
    try {
      const res = await fetch(`${API_BASE}/v1/watchlist/summary`, {
        headers: { 'X-API-Key': API_KEY }
      })
      if (res.ok) {
        const json = await res.json()
        setTapeData(json)
      }
    } catch (e) {
      console.error("Failed to fetch watchlist", e)
    }
  }

  const handleAddTicker = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTicker.trim()) return
    setIsAdding(true)
    try {
      await fetch(`${API_BASE}/v1/watchlist`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-API-Key': API_KEY
        },
        body: JSON.stringify({ ticker: newTicker.trim().toUpperCase() })
      })
      setNewTicker('')
      await fetchWatchlist()
    } catch (e) {
      console.error("Failed to add ticker", e)
    }
    setIsAdding(false)
  }

  const handleRemoveTicker = async (ticker: string) => {
    try {
      await fetch(`${API_BASE}/v1/watchlist/${ticker}`, {
        method: 'DELETE',
        headers: { 'X-API-Key': API_KEY }
      })
      await fetchWatchlist()
    } catch (e) {
      console.error("Failed to remove ticker", e)
    }
  }

  useEffect(() => {
    fetchWatchlist()
    const interval = setInterval(fetchWatchlist, 10000) // Poll every 10s
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="h-screen w-screen bg-background flex flex-col overflow-hidden">
      {/* Ticker Tape */}
      <TickerTape items={tapeData} onRemove={handleRemoveTicker} onClickTicker={(ticker) => setSelectedTicker(ticker)} />

      <div className="flex-1 flex flex-col p-2 min-h-0">
        <header className="flex items-center justify-between border-b border-border pb-2 mb-2 shrink-0">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold text-accent tracking-widest px-2">QUANT_XPR</h1>
          <span className="text-xs bg-panel px-2 py-1 border border-border text-muted-foreground font-bold tracking-widest">
            {data ? data.ticker : "LOADING"}
          </span>
          <form onSubmit={handleAddTicker} className="flex items-center ml-4">
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
        </div>
        <div className="text-xs font-bold tracking-widest text-bull px-4 animate-pulse">
          MARKET DATA CONNECTED
        </div>
      </header>

      {loading ? (
        <div className="flex-1 flex items-center justify-center text-accent animate-pulse font-bold tracking-widest">
          INITIALIZING QUADRANTS...
        </div>
      ) : (
        <div className="flex-1 grid grid-cols-2 grid-rows-2 gap-2 min-h-0">
          
          {/* Q1: Signal & Probabilities */}
          <div className="bg-panel border border-border p-4 overflow-hidden">
            <Q1Signal data={data} />
          </div>
          
          {/* Q2: Volatility Smile */}
          <div className="bg-panel border border-border p-4 overflow-hidden">
            <Q2Smile data={data} />
          </div>

          {/* Q3: Regime History (Candlesticks) */}
          <div className="bg-panel border border-border p-0 overflow-hidden">
            <Q3History data={data} />
          </div>

          {/* Q4: Signal Ledger (Table) */}
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
