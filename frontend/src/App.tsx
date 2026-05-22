import { useEffect, useState } from 'react'
import Q1Signal from './components/Q1Signal'
import Q2Smile from './components/Q2Smile'
import Q3History from './components/Q3History'
import Q4Table from './components/Q4Table'
import TickerTape, { TickerData } from './components/TickerTape'

// Helper to generate mock candlestick data
function generateMockRegimeHistory() {
  const data = [];
  let currentPrice = 100;
  const now = new Date();
  now.setUTCHours(0, 0, 0, 0);

  for (let i = 100; i >= 0; i--) {
    const time = new Date(now.getTime() - i * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
    const open = currentPrice + (Math.random() - 0.5) * 2;
    const close = open + (Math.random() - 0.5) * 4;
    const high = Math.max(open, close) + Math.random() * 2;
    const low = Math.min(open, close) - Math.random() * 2;
    currentPrice = close;
    
    data.push({ time, open, high, low, close });
  }
  return data;
}

const mockTapeAssets: TickerData[] = [
  { ticker: "SPY", signal: "RISK_REVERSAL", iv_atm: 0.15 },
  { ticker: "QQQ", signal: "long_vol", iv_atm: 0.18 },
  { ticker: "PETR4.SA", signal: "short_vol", iv_atm: 0.28 },
  { ticker: "VALE3.SA", signal: "neutral", iv_atm: 0.32 },
  { ticker: "BOVA11.SA", signal: "RISK_REVERSAL", iv_atm: 0.22 },
];

function App() {
  const [data, setData] = useState<any>(null)
  const [history, setHistory] = useState<any[]>([])
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
        smile_data: [
          { strike: 30, impliedVolatility: 0.35 },
          { strike: 32, impliedVolatility: 0.31 },
          { strike: 34, impliedVolatility: 0.29 },
          { strike: 36, impliedVolatility: 0.28 }, // ATM approx
          { strike: 38, impliedVolatility: 0.285 },
          { strike: 40, impliedVolatility: 0.32 },
          { strike: 42, impliedVolatility: 0.38 },
        ],
        regime_history: generateMockRegimeHistory()
      })

      setHistory([
        { timestamp: new Date().toISOString(), ticker: "PETR4.SA", signal: "RISK_REVERSAL", markov_bull_prob: 0.85, skew: 0.045 },
        { timestamp: new Date(Date.now() - 86400000).toISOString(), ticker: "VALE3.SA", signal: "short_vol", markov_bull_prob: 0.35, skew: -0.02 },
        { timestamp: new Date(Date.now() - 172800000).toISOString(), ticker: "ITUB4.SA", signal: "neutral", markov_bull_prob: 0.50, skew: 0.01 },
        { timestamp: new Date(Date.now() - 259200000).toISOString(), ticker: "PETR4.SA", signal: "long_vol", markov_bull_prob: 0.70, skew: 0.03 },
        { timestamp: new Date(Date.now() - 345600000).toISOString(), ticker: "BBDC4.SA", signal: "error_fetching", markov_bull_prob: 0.00, skew: 0.00 },
      ])
      
      setLoading(false)
    }, 800)
  }, [])

  return (
    <div className="h-screen w-screen bg-background flex flex-col overflow-hidden">
      {/* Ticker Tape */}
      <TickerTape items={mockTapeAssets} />

      <div className="flex-1 flex flex-col p-2 min-h-0">
        <header className="flex items-center justify-between border-b border-border pb-2 mb-2 shrink-0">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold text-accent tracking-widest px-2">QUANT_XPR</h1>
          <span className="text-xs bg-panel px-2 py-1 border border-border text-muted-foreground font-bold tracking-widest">
            {data ? data.ticker : "LOADING"}
          </span>
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
