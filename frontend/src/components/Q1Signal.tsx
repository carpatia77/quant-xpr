import { TrendingUp, TrendingDown, Activity, Edit2, Check, X } from "lucide-react";
import { useState } from "react";

interface Q1SignalProps {
  data: any;
  onOverrideRfr?: (val: number | null) => void;
}

export default function Q1Signal({ data, onOverrideRfr }: Q1SignalProps) {
  const [isEditingRfr, setIsEditingRfr] = useState(false);
  const [rfrInput, setRfrInput] = useState("");

  if (!data) return <div className="h-full flex items-center justify-center text-muted-foreground animate-pulse">Awaiting Data...</div>;

  const sig = data.signal ? data.signal.toLowerCase() : "";
  const isBull = sig === "risk_reversal" || sig === "long_vol" || sig === "directional_bull";

  const handleRfrSubmit = () => {
    const val = parseFloat(rfrInput);
    if (!isNaN(val) && onOverrideRfr) {
      onOverrideRfr(val);
    }
    setIsEditingRfr(false);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm text-muted-foreground font-bold tracking-widest flex items-center gap-2">
          <Activity size={16} /> SIGNAL & PROBABILITIES
        </h2>
        <span className="text-xs bg-panel border border-border px-2 py-1 text-muted-foreground">LIVE</span>
      </div>

      {/* Main Signal Display */}
      <div className="flex-1 flex flex-col justify-center items-center mb-6">
        <div className={`text-sm tracking-widest font-bold px-3 py-1 mb-2 ${isBull ? 'bg-bull/20 text-bull' : 'bg-bear/20 text-bear'}`}>
          CURRENT BIAS
        </div>
        <div className={`text-4xl font-bold ${isBull ? 'text-bull' : 'text-bear'} flex items-center gap-3 mb-3`}>
          {isBull ? <TrendingUp size={40} /> : <TrendingDown size={40} />}
          {data.signal.replace(/_/g, " ")}
        </div>
        
        {data.risk_free_rate_source && (
          <div className="text-xs bg-amber-500/20 text-amber-500 border border-amber-500/50 px-3 py-1 rounded font-bold tracking-widest flex items-center gap-2 group cursor-pointer transition-colors hover:bg-amber-500/30">
            {isEditingRfr ? (
              <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                <input 
                  type="number" 
                  step="0.01"
                  autoFocus
                  placeholder="ex: 10.5"
                  className="bg-background text-foreground border border-amber-500/50 w-20 px-1 py-0.5 outline-none"
                  value={rfrInput}
                  onChange={(e) => setRfrInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleRfrSubmit()}
                />
                <span className="text-[10px]">%</span>
                <button onClick={handleRfrSubmit} className="hover:text-amber-300 ml-1"><Check size={14} /></button>
                <button onClick={() => { setIsEditingRfr(false); if(onOverrideRfr) onOverrideRfr(null); }} className="hover:text-bear"><X size={14} /></button>
              </div>
            ) : (
              <div className="flex items-center gap-2" onClick={() => { setIsEditingRfr(true); setRfrInput((data.risk_free_rate * 100).toFixed(2)); }}>
                {data.risk_free_rate_source.toUpperCase().split(' (')[0]} {(data.risk_free_rate * 100).toFixed(2)}%
                <Edit2 size={12} className="opacity-0 group-hover:opacity-100" />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Markov Probabilities */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <div className="flex justify-between text-xs font-bold">
            <span className="text-muted-foreground">MARKOV BULL PROB</span>
            <span className="text-bull">{(data.markov_bull_prob * 100).toFixed(1)}%</span>
          </div>
          <div className="h-2 w-full bg-background border border-border overflow-hidden">
            <div 
              className="h-full bg-bull transition-all duration-1000 ease-out" 
              style={{ width: `${data.markov_bull_prob * 100}%` }}
            />
          </div>
        </div>

        <div className="flex flex-col gap-1">
          <div className="flex justify-between text-xs font-bold">
            <span className="text-muted-foreground">MARKOV BEAR PROB</span>
            <span className="text-bear">{(data.markov_bear_prob * 100).toFixed(1)}%</span>
          </div>
          <div className="h-2 w-full bg-background border border-border overflow-hidden">
            <div 
              className="h-full bg-bear transition-all duration-1000 ease-out" 
              style={{ width: `${data.markov_bear_prob * 100}%` }}
            />
          </div>
        </div>
      </div>

      <div className="mt-auto pt-4 grid grid-cols-2 gap-4 border-t border-border mt-4">
        <div className="flex flex-col">
          <span className="text-[10px] text-muted-foreground tracking-widest">SKEW</span>
          <span className="text-lg text-accent">{(data.skew * 100).toFixed(2)}%</span>
        </div>
        <div className="flex flex-col">
          <span className="text-[10px] text-muted-foreground tracking-widest">RISK FREE RATE</span>
          <span className="text-lg text-foreground">{(data.risk_free_rate * 100).toFixed(2)}%</span>
        </div>
      </div>
    </div>
  );
}
