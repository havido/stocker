import { TrendingUp, TrendingDown, Minus, BarChart3 } from "lucide-react";

export interface SentimentData {
  positive: number;
  negative: number;
  neutral: number;
  average_positive_score: number;
  average_negative_score: number;
  average_neutral_score: number;
  verdict: string;
}

interface SentimentResultsProps {
  data: SentimentData;
  ticker: string;
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const config: Record<string, { bg: string; text: string; border: string; icon: React.ReactNode }> = {
    positive: {
      bg: "bg-positive/10",
      text: "text-positive",
      border: "border-positive/30",
      icon: <TrendingUp className="h-5 w-5" />,
    },
    negative: {
      bg: "bg-negative/10",
      text: "text-negative",
      border: "border-negative/30",
      icon: <TrendingDown className="h-5 w-5" />,
    },
    neutral: {
      bg: "bg-neutral/10",
      text: "text-neutral",
      border: "border-neutral/30",
      icon: <Minus className="h-5 w-5" />,
    },
  };

  const c = config[verdict] || config.neutral;

  return (
    <div className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-full border ${c.bg} ${c.border}`}>
      <span className={c.text}>{c.icon}</span>
      <span className={`text-sm font-bold uppercase tracking-wider ${c.text}`}>
        {verdict}
      </span>
    </div>
  );
}

function SentimentBar({ positive, negative, neutral }: { positive: number; negative: number; neutral: number }) {
  const total = positive + negative + neutral;
  if (total === 0) return null;

  const pPct = (positive / total) * 100;
  const nPct = (negative / total) * 100;
  const neuPct = (neutral / total) * 100;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs font-medium text-muted-foreground">
        <span>Sentiment Distribution</span>
        <span>{total} articles analyzed</span>
      </div>
      <div className="h-3 w-full rounded-full overflow-hidden flex bg-secondary">
        <div
          className="h-full transition-all duration-700 ease-out"
          style={{
            width: `${pPct}%`,
            background: "hsl(var(--positive))",
          }}
        />
        <div
          className="h-full transition-all duration-700 ease-out"
          style={{
            width: `${neuPct}%`,
            background: "hsl(var(--neutral))",
          }}
        />
        <div
          className="h-full transition-all duration-700 ease-out"
          style={{
            width: `${nPct}%`,
            background: "hsl(var(--negative))",
          }}
        />
      </div>
      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1.5">
          <div className="h-2.5 w-2.5 rounded-full" style={{ background: "hsl(var(--positive))" }} />
          <span className="text-muted-foreground">Positive {pPct.toFixed(1)}%</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="h-2.5 w-2.5 rounded-full" style={{ background: "hsl(var(--neutral))" }} />
          <span className="text-muted-foreground">Neutral {neuPct.toFixed(1)}%</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="h-2.5 w-2.5 rounded-full" style={{ background: "hsl(var(--negative))" }} />
          <span className="text-muted-foreground">Negative {nPct.toFixed(1)}%</span>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  count,
  confidence,
  color,
  icon,
}: {
  label: string;
  count: number;
  confidence: number;
  color: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 hover:shadow-lg hover:shadow-primary/5 transition-all duration-300 group">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          {label}
        </span>
        <span className={color}>{icon}</span>
      </div>
      <div className="flex items-end gap-2">
        <span className="text-3xl font-bold">{count}</span>
        <span className="text-xs text-muted-foreground mb-1">articles</span>
      </div>
      <div className="mt-3 space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Avg. Confidence</span>
          <span className="font-semibold">{(confidence * 100).toFixed(1)}%</span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700 ease-out"
            style={{
              width: `${confidence * 100}%`,
              background: `hsl(var(--${label.toLowerCase()}))`,
            }}
          />
        </div>
      </div>
    </div>
  );
}

function SentimentGaugeRing({ data }: { data: SentimentData }) {
  const total = data.positive + data.negative + data.neutral;
  if (total === 0) return null;

  const segments = [
    { label: "Positive", count: data.positive, color: "hsl(var(--positive))" },
    { label: "Neutral", count: data.neutral, color: "hsl(var(--neutral))" },
    { label: "Negative", count: data.negative, color: "hsl(var(--negative))" },
  ];

  const radius = 70;
  const circumference = 2 * Math.PI * radius;
  let cumulativeOffset = 0;

  return (
    <div className="flex flex-col items-center">
      <div className="relative">
        <svg width="180" height="180" viewBox="0 0 180 180">
          {segments.map((seg, i) => {
            const pct = seg.count / total;
            const dashLength = pct * circumference;
            const dashOffset = -cumulativeOffset;
            cumulativeOffset += dashLength;

            return (
              <circle
                key={i}
                cx="90"
                cy="90"
                r={radius}
                fill="none"
                stroke={seg.color}
                strokeWidth="12"
                strokeDasharray={`${dashLength} ${circumference - dashLength}`}
                strokeDashoffset={dashOffset}
                strokeLinecap="round"
                className="transition-all duration-700 ease-out"
                style={{
                  transform: "rotate(-90deg)",
                  transformOrigin: "50% 50%",
                }}
              />
            );
          })}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold">{total}</span>
          <span className="text-xs text-muted-foreground">Total</span>
        </div>
      </div>
    </div>
  );
}

export function SentimentResults({ data, ticker }: SentimentResultsProps) {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Top verdict card */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
              <BarChart3 className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-bold">
                Sentiment Analysis for <span className="text-primary">${ticker}</span>
              </h2>
              <p className="text-sm text-muted-foreground">
                Based on {data.positive + data.negative + data.neutral} scraped articles
              </p>
            </div>
          </div>
          <VerdictBadge verdict={data.verdict} />
        </div>
      </div>

      {/* Donut + Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-2 rounded-xl border border-border bg-card p-6 flex flex-col items-center justify-center">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">
            Breakdown
          </h3>
          <SentimentGaugeRing data={data} />
        </div>
        <div className="lg:col-span-3 rounded-xl border border-border bg-card p-6 flex flex-col justify-center">
          <SentimentBar
            positive={data.positive}
            negative={data.negative}
            neutral={data.neutral}
          />
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          label="Positive"
          count={data.positive}
          confidence={data.average_positive_score}
          color="text-positive"
          icon={<TrendingUp className="h-5 w-5" />}
        />
        <StatCard
          label="Neutral"
          count={data.neutral}
          confidence={data.average_neutral_score}
          color="text-neutral"
          icon={<Minus className="h-5 w-5" />}
        />
        <StatCard
          label="Negative"
          count={data.negative}
          confidence={data.average_negative_score}
          color="text-negative"
          icon={<TrendingDown className="h-5 w-5" />}
        />
      </div>
    </div>
  );
}
