import { useEffect, useRef } from 'react';
import { createChart, ColorType, CrosshairMode } from 'lightweight-charts';

interface Q3HistoryProps {
  data: any;
}

export default function Q3History({ data }: Q3HistoryProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;
    if (!data || !data.regime_history || data.regime_history.length === 0) return;

    // Create chart instance
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#131B2B' },
        textColor: '#888',
      },
      grid: {
        vertLines: { color: '#333' },
        horzLines: { color: '#333' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: '#333',
      },
      timeScale: {
        borderColor: '#333',
        timeVisible: true,
      },
    });

    const candlestickSeries = (chart as any).addCandlestickSeries({
      upColor: '#00d4aa',
      downColor: '#ff4757',
      borderVisible: false,
      wickUpColor: '#00d4aa',
      wickDownColor: '#ff4757',
    });

    // Format data for lightweight-charts
    // Assuming data.regime_history has: time, open, high, low, close, regime
    const seriesData = data.regime_history.map((d: any) => ({
      time: d.time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));

    candlestickSeries.setData(seriesData);

    // Fit content
    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data]);

  if (!data || !data.regime_history || data.regime_history.length === 0) {
    return <div className="h-full flex items-center justify-center text-muted-foreground animate-pulse">Awaiting Regime Data...</div>;
  }

  return (
    <div className="flex flex-col h-full relative">
      <div className="flex items-center justify-between mb-4 absolute top-0 left-0 w-full z-10 px-4 pt-4 pointer-events-none">
        <h2 className="text-sm text-muted-foreground font-bold tracking-widest bg-panel/80 px-2 rounded">
          REGIME HISTORY (MARKOV)
        </h2>
        <span className="text-xs bg-panel/80 border border-border px-2 py-1 text-muted-foreground">LIGHTWEIGHT CHARTS</span>
      </div>
      {/* Chart Container */}
      <div ref={chartContainerRef} className="flex-1 w-full h-full" />
    </div>
  );
}
