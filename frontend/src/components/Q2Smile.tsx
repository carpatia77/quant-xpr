import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

interface Q2SmileProps {
  data: any;
}

export default function Q2Smile({ data }: Q2SmileProps) {
  if (!data || !data.smile_data || data.smile_data.length === 0) {
    return <div className="h-full flex items-center justify-center text-muted-foreground animate-pulse">Awaiting Smile Data...</div>;
  }

  // Pre-process smile data for Recharts
  const chartData = data.smile_data.map((d: any) => ({
    strike: d.strike,
    iv: d.impliedVolatility * 100,
  }));

  // Find ATM strike approximately for a reference line
  // In a real scenario we'd use current spot/forward price.
  const strikes = chartData.map((d: any) => d.strike);
  const midStrike = strikes[Math.floor(strikes.length / 2)];

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm text-muted-foreground font-bold tracking-widest">
          VOLATILITY SMILE (OOM)
        </h2>
        <span className="text-xs bg-panel border border-border px-2 py-1 text-muted-foreground">RECHARTS</span>
      </div>

      <div className="flex-1 w-full min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis 
              dataKey="strike" 
              stroke="#666" 
              tick={{ fill: '#888', fontSize: 11 }}
              domain={['dataMin', 'dataMax']}
              type="number"
            />
            <YAxis 
              stroke="#666" 
              tick={{ fill: '#888', fontSize: 11 }}
              domain={['auto', 'auto']}
              tickFormatter={(val) => `${val.toFixed(1)}%`}
            />
            <Tooltip 
              contentStyle={{ backgroundColor: '#131B2B', borderColor: '#333', color: '#e0e0e0', fontSize: '12px' }}
              itemStyle={{ color: '#f5a623' }}
              formatter={(value: any) => [`${Number(value).toFixed(2)}%`, 'Implied Vol']}
              labelFormatter={(label) => `Strike: ${label}`}
            />
            <ReferenceLine x={midStrike} stroke="#666" strokeDasharray="3 3" label={{ position: 'top', value: 'ATM', fill: '#888', fontSize: 10 }} />
            <Line 
              type="monotone" 
              dataKey="iv" 
              stroke="#f5a623" 
              strokeWidth={2}
              dot={{ r: 3, fill: '#1a1a1a', stroke: '#f5a623', strokeWidth: 2 }}
              activeDot={{ r: 6, fill: '#f5a623' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
