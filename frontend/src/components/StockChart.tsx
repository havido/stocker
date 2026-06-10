import { useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { TrendingUp, TrendingDown, AlertCircle, RefreshCw } from "lucide-react";

export interface PricePoint {
  time: string;
  price: number;
}

export interface StockChartData {
  ticker: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  history: Record<string, PricePoint[]>;
}

const PERIODS = ["1D", "1M", "6M", "YTD", "1Y", "5Y", "10Y"] as const;

interface StockChartProps {
  data: StockChartData | null;
  loading: boolean;
  error?: string | null;
  onRetry?: () => void;
}

export function StockChart({ data, loading, error, onRetry }: StockChartProps) {
  const [period, setPeriod] = useState<string>("1D");

  if (loading) {
    return (
      <div className="rounded-xl border border-border bg-card p-6 space-y-4 animate-pulse">
        <div className="h-6 w-40 bg-muted rounded" />
        <div className="h-4 w-24 bg-muted rounded" />
        <div className="h-[300px] bg-muted rounded-lg" />
        <div className="flex gap-2">
          {PERIODS.map((p) => (
            <div key={p} className="h-8 w-12 bg-muted rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="rounded-xl border border-border bg-card p-6 flex flex-col items-center justify-center text-center gap-3 min-h-[360px]">
        <div className="h-12 w-12 rounded-xl bg-muted/50 flex items-center justify-center">
          <AlertCircle className="h-6 w-6 text-muted-foreground" />
        </div>
        <p className="text-sm font-medium">Couldn't load the chart</p>
        <p className="text-xs text-muted-foreground max-w-xs">{error}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-1 inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-secondary text-muted-foreground hover:text-foreground transition-all"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Retry
          </button>
        )}
      </div>
    );
  }

  if (!data) return null;

  const chartData: PricePoint[] = data.history[period] ?? [];

  // Gain/loss must reflect the SELECTED period — from the first point in the
  // visible range to the current price — not the backend's 1-day change.
  const startPrice = chartData[0]?.price ?? 0;
  const hasRange = chartData.length > 0 && startPrice !== 0;
  const periodChange = hasRange ? data.price - startPrice : data.change;
  const periodChangePct = hasRange ? (periodChange / startPrice) * 100 : data.changePercent;
  const isPositive = periodChange >= 0;

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="mb-1 flex items-baseline gap-3">
        <h2 className="text-2xl font-bold">{data.ticker}</h2>
        {data.name && data.name !== data.ticker && (
          <span className="text-sm text-muted-foreground font-medium">{data.name}</span>
        )}
      </div>
      <div className="flex items-center gap-2 mb-6">
        <span className="text-3xl font-bold">${data.price.toFixed(2)}</span>
        <span
          className={`flex items-center gap-1 text-sm font-semibold ${
            isPositive ? "text-positive" : "text-negative"
          }`}
        >
          {isPositive ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
          {isPositive ? "+" : ""}
          {periodChangePct.toFixed(2)}%
        </span>
        <span className="text-sm text-muted-foreground">
          ({isPositive ? "+" : ""}${periodChange.toFixed(2)})
        </span>
      </div>

      <div className="h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="hsl(var(--chart-grid))"
              vertical={false}
            />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 11 }}
              stroke="hsl(var(--muted-foreground))"
              tickLine={false}
              axisLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={["auto", "auto"]}
              tick={{ fontSize: 11 }}
              stroke="hsl(var(--muted-foreground))"
              tickLine={false}
              axisLine={false}
              width={60}
              tickFormatter={(v: number) => `$${v}`}
            />
            <Tooltip
              contentStyle={{
                background: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
                fontSize: "13px",
              }}
              labelStyle={{ color: "hsl(var(--muted-foreground))" }}
              formatter={(value: number) => [`$${value.toFixed(2)}`, "Price"]}
            />
            <Line
              type="monotone"
              dataKey="price"
              stroke={isPositive ? "hsl(var(--positive))" : "hsl(var(--negative))"}
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 5, strokeWidth: 0 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="flex gap-1.5 mt-4">
        {PERIODS.map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              period === p
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-muted-foreground hover:text-foreground"
            }`}
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}
