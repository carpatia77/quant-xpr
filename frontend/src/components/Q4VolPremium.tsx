interface Q4VolPremiumProps {
  data: any;
  loading: boolean;
  error: string | null;
}

export const Q4VolPremium: React.FC<Q4VolPremiumProps> = ({ data, loading, error }) => {
  if (loading) {
    return (
      <div className="bg-surface border border-border p-4 rounded flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-surface border border-border p-4 rounded flex items-center justify-center h-full text-danger text-sm">
        {error || "Awaiting Data..."}
      </div>
    );
  }

  const volPremium = data.vol_premium;

  if (!volPremium || volPremium.error) {
    return (
      <div className="bg-surface border border-border p-4 rounded flex flex-col justify-between h-full">
        <div>
          <h2 className="text-xl font-bold text-accent mb-1 tracking-tight">Q4: VOLATILITY PREMIUM</h2>
          <div className="text-muted text-xs mb-4 border-b border-border pb-2">TERM STRUCTURE & RISK PREMIUM</div>
        </div>
        <div className="flex-1 flex items-center justify-center text-muted text-sm px-4 text-center">
          {volPremium?.error || "Term Structure Data Unavailable. Needs Multiple Option Expirations."}
        </div>
      </div>
    );
  }

  // Determine badge color
  let badgeColor = "text-danger border-danger/30 bg-danger/10";
  if (volPremium.bias_recommendation === "Recommended") badgeColor = "text-success border-success/30 bg-success/10";
  if (volPremium.bias_recommendation === "Consider") badgeColor = "text-warning border-warning/30 bg-warning/10";

  return (
    <div className="bg-surface border border-border p-4 rounded flex flex-col justify-between h-full">
      <div>
        <h2 className="text-xl font-bold text-accent mb-1 tracking-tight">Q4: VOLATILITY PREMIUM</h2>
        <div className="text-muted text-xs mb-4 border-b border-border pb-2">TERM STRUCTURE & RISK PREMIUM</div>
      </div>

      <div className="flex flex-col gap-4">
        {/* Recommendation Badge */}
        <div className="flex justify-between items-center bg-background/50 p-3 rounded border border-border">
          <span className="text-muted text-sm font-medium">Bias Recommendation</span>
          <span className={`px-3 py-1 rounded text-sm font-bold border ${badgeColor}`}>
            {volPremium.bias_recommendation.toUpperCase()}
          </span>
        </div>

        {/* Expected Move */}
        <div className="flex justify-between items-center px-2">
          <span className="text-muted text-sm">ATM Straddle Expected Move</span>
          <span className="text-accent text-lg font-mono font-bold">
            {volPremium.expected_move_pct.toFixed(2)}%
          </span>
        </div>

        {/* Detailed Metrics */}
        <div className="space-y-2 mt-2">
          {/* IV30 / RV30 */}
          <div className="flex justify-between items-center text-sm px-2">
            <span className="text-muted flex gap-2">
              <span className={`w-2 h-2 mt-1.5 rounded-full ${volPremium.iv30_rv30_pass ? "bg-success" : "bg-danger"}`}></span>
              IV30 / RV30 Ratio (&ge; 1.25)
            </span>
            <span className="font-mono text-text">{volPremium.iv30_rv30.toFixed(2)}x</span>
          </div>

          {/* Term Structure Slope */}
          <div className="flex justify-between items-center text-sm px-2">
            <span className="text-muted flex gap-2">
              <span className={`w-2 h-2 mt-1.5 rounded-full ${volPremium.ts_slope_pass ? "bg-success" : "bg-danger"}`}></span>
              TS Slope 0-45d (&le; -0.004)
            </span>
            <span className="font-mono text-text">{volPremium.ts_slope_0_45.toFixed(5)}</span>
          </div>

          {/* Volume */}
          <div className="flex justify-between items-center text-sm px-2">
            <span className="text-muted flex gap-2">
              <span className={`w-2 h-2 mt-1.5 rounded-full ${volPremium.avg_volume_pass ? "bg-success" : "bg-danger"}`}></span>
              30d Avg Volume (&ge; 1.5M)
            </span>
            <span className="font-mono text-text">
              {(volPremium.avg_volume / 1000000).toFixed(2)}M
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
