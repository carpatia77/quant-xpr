import { TrendingUp, TrendingDown, Minus, X } from "lucide-react";

export interface TickerData {
  ticker: string;
  signal: string;
  iv_atm: number;
}

interface TickerTapeProps {
  items: TickerData[];
  onRemove?: (ticker: string) => void;
}

export default function TickerTape({ items, onRemove }: TickerTapeProps) {
  if (!items || items.length === 0) return (
    <div className="w-full bg-[#0A0E17] border-b border-border py-1.5 flex items-center justify-center text-xs text-muted-foreground shrink-0">
      Watchlist is empty
    </div>
  );

  // Duplicate items to create a seamless infinite scroll effect
  const repeatedItems = [...items, ...items, ...items, ...items];

  return (
    <div className="w-full bg-[#0A0E17] border-b border-border overflow-hidden py-1.5 flex items-center shrink-0">
      <div className="flex w-max animate-marquee hover:[animation-play-state:paused]">
        {repeatedItems.map((item, index) => {
          let colorClass = "text-muted-foreground";
          let Icon = Minus;

          if (item.signal === "RISK_REVERSAL" || item.signal === "long_vol") {
            colorClass = "text-bull";
            Icon = TrendingUp;
          } else if (item.signal === "short_vol") {
            colorClass = "text-bear";
            Icon = TrendingDown;
          }

          return (
            <div key={index} className="flex items-center gap-2 px-6 border-r border-border/30 last:border-0 shrink-0 group">
              <span className="font-bold text-xs tracking-widest text-foreground">
                {item.ticker}
              </span>
              <Icon size={14} className={colorClass} />
              <span className={`text-xs font-bold ${colorClass}`}>
                {item.signal.replace(/_/g, " ")}
              </span>
              <span className="text-xs text-accent tracking-widest ml-1">
                IV: {(item.iv_atm * 100).toFixed(1)}%
              </span>
              {onRemove && (
                <button 
                  onClick={() => onRemove(item.ticker)}
                  className="ml-2 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-bear transition-opacity cursor-pointer"
                  title="Remove from Watchlist"
                >
                  <X size={12} />
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
