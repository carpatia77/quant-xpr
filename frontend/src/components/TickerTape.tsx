import { TrendingUp, TrendingDown, Minus, X } from "lucide-react";

export interface TickerData {
  ticker: string;
  signal: string;
  iv_atm: number;
  price?: number;
  change_percent?: number;
}

interface TickerTapeProps {
  items: TickerData[];
  onRemove?: (ticker: string) => void;
  onClickTicker?: (ticker: string) => void;
}

export default function TickerTape({ items, onRemove, onClickTicker }: TickerTapeProps) {
  if (!items || items.length === 0) return (
    <div className="w-full bg-[#0A0E17] border-b border-border py-1.5 flex items-center justify-center text-xs text-muted-foreground shrink-0">
      Watchlist is empty
    </div>
  );

  // Pad items so the marquee always has enough content to overflow the screen
  let baseItems = [...items];
  while (baseItems.length < 15) {
    baseItems = [...baseItems, ...items];
  }
  
  // Duplicate the padded items once to create the seamless -50% translation loop
  const repeatedItems = [...baseItems, ...baseItems];

  return (
    <div className="w-full bg-[#0A0E17] border-b border-border overflow-hidden py-1.5 flex items-center shrink-0">
      <div className="flex w-max animate-marquee hover:[animation-play-state:paused]">
        {repeatedItems.map((item, index) => {
          const sig = item.signal ? item.signal.toLowerCase() : "";
          const isBull = sig === "risk_reversal" || sig === "long_vol" || sig === "directional_bull";
          const isBear = sig.includes("bear");
          
          const signalColor = sig === "error_fetching_data" || sig === "waiting_data" 
            ? "text-muted-foreground"
            : isBull ? "text-bull" : isBear ? "text-bear" : "text-foreground";
          
          const Icon = sig === "error_fetching_data" || sig === "waiting_data"
            ? Activity 
            : isBull ? TrendingUp : TrendingDown;

          const hasMarketData = item.price !== undefined && item.price > 0;
          const changeColor = item.change_percent !== undefined && item.change_percent >= 0 ? "text-bull" : "text-bear";

          return (
            <div key={index} className="flex items-center gap-2 px-6 border-r border-border/30 last:border-0 shrink-0 group">
              <span 
                className="font-bold text-xs tracking-widest text-foreground cursor-pointer hover:text-accent transition-colors"
                onClick={() => onClickTicker && onClickTicker(item.ticker)}
              >
                {item.ticker}
              </span>

              {hasMarketData && (
                <span className="text-xs font-bold text-foreground">
                  R$ {item.price?.toFixed(2)}
                </span>
              )}
              {hasMarketData && item.change_percent !== undefined && (
                <span className={`text-xs font-bold ${changeColor}`}>
                  {item.change_percent >= 0 ? "+" : ""}{item.change_percent.toFixed(2)}%
                </span>
              )}

              <span className="text-muted-foreground/30 mx-1">|</span>

              {item.signal && item.signal !== "WAITING_DATA" && !item.signal.startsWith("error") ? (
                <>
                  <Icon size={14} className={signalColor} />
                  <span className={`text-xs font-bold ${signalColor}`}>
                    {item.signal.replace(/_/g, " ")}
                  </span>
                  <span className="text-xs text-accent tracking-widest ml-1">
                    IV: {(item.iv_atm * 100).toFixed(1)}%
                  </span>
                </>
              ) : (
                <span className="text-xs text-muted-foreground italic">
                  Awaiting Analytics...
                </span>
              )}

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
