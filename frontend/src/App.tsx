import { useEffect, useState } from 'react'

function App() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Mocking an API call for now to build the UI structure
    setTimeout(() => {
      setData({
        ticker: "PETR4.SA",
        signal: "RISK_REVERSAL",
        markov_bull_prob: 0.85,
        markov_bear_prob: 0.05,
        iv_atm: 0.28,
        skew: 0.045,
        risk_free_rate: 0.144,
      })
      setLoading(false)
    }, 1000)
  }, [])

  return (
    <div className="min-h-screen p-4 flex flex-col gap-4">
      <header className="flex items-center justify-between border-b border-border pb-4">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold text-accent tracking-widest">QUANT_XPR</h1>
          <span className="text-sm bg-panel px-2 py-1 border border-border text-muted-foreground">TERMINAL v2.0</span>
        </div>
        <div className="text-xs text-muted-foreground">STATUS: CONNECTED</div>
      </header>

      {loading ? (
        <div className="flex-1 flex items-center justify-center text-accent animate-pulse">
          LOADING DATA...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Main Info Panel */}
          <div className="bg-panel border border-border p-4 flex flex-col gap-2">
            <h2 className="text-sm text-muted-foreground uppercase tracking-wider mb-2">Asset Details</h2>
            <div className="flex justify-between items-baseline">
              <span className="text-3xl font-bold">{data.ticker}</span>
              <span className={`text-xs px-2 py-1 uppercase tracking-widest font-bold ${
                data.signal === 'RISK_REVERSAL' ? 'bg-bull text-background' : 'bg-bear text-foreground'
              }`}>
                {data.signal}
              </span>
            </div>
            
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground">BULL PROB</span>
                <span className="text-lg text-bull">{(data.markov_bull_prob * 100).toFixed(1)}%</span>
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground">BEAR PROB</span>
                <span className="text-lg text-bear">{(data.markov_bear_prob * 100).toFixed(1)}%</span>
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground">IV ATM</span>
                <span className="text-lg">{(data.iv_atm * 100).toFixed(1)}%</span>
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground">SKEW</span>
                <span className="text-lg text-accent">{(data.skew * 100).toFixed(2)}%</span>
              </div>
            </div>
          </div>
          
          {/* Market Data Panel */}
          <div className="bg-panel border border-border p-4 flex flex-col gap-2 col-span-2">
            <h2 className="text-sm text-muted-foreground uppercase tracking-wider mb-2">Macro & Yields</h2>
            <div className="flex gap-12">
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground">RISK FREE RATE (BCB)</span>
                <span className="text-xl text-accent">{(data.risk_free_rate * 100).toFixed(2)}%</span>
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground">FORWARD ADJUSTED</span>
                <span className="text-xl text-bull">ACTIVE</span>
              </div>
            </div>
            <div className="mt-6 border border-border bg-background p-4 flex items-center justify-center text-muted-foreground text-sm">
              [ VOLATILITY TERM STRUCTURE CHART AREA ]
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
