import { useState } from 'react';

interface Q4TableProps {
  historyData: any[];
}

export default function Q4Table({ historyData }: Q4TableProps) {
  const [filter, setFilter] = useState('');

  if (!historyData || historyData.length === 0) {
    return <div className="h-full flex items-center justify-center text-muted-foreground animate-pulse">Awaiting History Log...</div>;
  }

  const filtered = historyData.filter(d => 
    d.ticker.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm text-muted-foreground font-bold tracking-widest">
          SIGNAL LEDGER
        </h2>
        <input 
          type="text" 
          placeholder="Filter Ticker..." 
          className="bg-background border border-border px-2 py-1 text-xs text-foreground focus:outline-none focus:border-accent"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      <div className="flex-1 overflow-auto border border-border">
        <table className="w-full text-left text-xs border-collapse">
          <thead className="bg-background sticky top-0 border-b border-border">
            <tr>
              <th className="px-3 py-2 font-medium text-muted-foreground uppercase">Timestamp</th>
              <th className="px-3 py-2 font-medium text-muted-foreground uppercase">Ticker</th>
              <th className="px-3 py-2 font-medium text-muted-foreground uppercase">Signal</th>
              <th className="px-3 py-2 font-medium text-muted-foreground uppercase text-right">Bull %</th>
              <th className="px-3 py-2 font-medium text-muted-foreground uppercase text-right">Skew %</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((row, i) => {
              const isBull = row.signal === "RISK_REVERSAL" || row.signal === "long_vol";
              return (
                <tr key={i} className="border-b border-border/50 hover:bg-white/5 transition-colors">
                  <td className="px-3 py-2 text-muted-foreground">{new Date(row.timestamp).toISOString().replace('T', ' ').slice(0, 19)}</td>
                  <td className="px-3 py-2 font-bold">{row.ticker}</td>
                  <td className={`px-3 py-2 font-bold ${isBull ? 'text-bull' : 'text-bear'}`}>{row.signal}</td>
                  <td className="px-3 py-2 text-right">{(row.markov_bull_prob * 100).toFixed(1)}%</td>
                  <td className="px-3 py-2 text-right">{(row.skew * 100).toFixed(2)}%</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
