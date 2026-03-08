import { type SentimentSource, MOCK_SOURCES, MOCK_SENTIMENT_SCORE } from "@/lib/mockData";
import { Twitter, MessageCircle, Newspaper, TrendingUp, TrendingDown, Minus } from "lucide-react";

interface SentimentPanelProps {
  loading: boolean;
}

function SentimentGauge({ score, loading }: { score: number; loading: boolean }) {
  if (loading) {
    return (
      <div className="flex flex-col items-center gap-3 py-4 animate-pulse">
        <div className="h-32 w-64 bg-muted rounded-t-full" />
        <div className="h-4 w-20 bg-muted rounded" />
      </div>
    );
  }

  // Map score from [-1, 1] to [0, 180] degrees
  const angle = ((score + 1) / 2) * 180;
  const label = score > 0.3 ? "Bullish" : score < -0.3 ? "Bearish" : "Neutral";
  const labelColor = score > 0.3 ? "text-positive" : score < -0.3 ? "text-negative" : "text-neutral";

  return (
    <div className="flex flex-col items-center py-4">
      <div className="relative w-56 h-28 overflow-hidden">
        {/* Background arc */}
        <svg viewBox="0 0 200 100" className="w-full h-full">
          <defs>
            <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="hsl(var(--negative))" />
              <stop offset="50%" stopColor="hsl(var(--neutral))" />
              <stop offset="100%" stopColor="hsl(var(--positive))" />
            </linearGradient>
          </defs>
          <path
            d="M 10 95 A 90 90 0 0 1 190 95"
            fill="none"
            stroke="hsl(var(--border))"
            strokeWidth="14"
            strokeLinecap="round"
          />
          <path
            d="M 10 95 A 90 90 0 0 1 190 95"
            fill="none"
            stroke="url(#gaugeGrad)"
            strokeWidth="14"
            strokeLinecap="round"
            opacity="0.3"
          />
          {/* Needle */}
          <line
            x1="100"
            y1="95"
            x2={100 + 70 * Math.cos((Math.PI * (180 - angle)) / 180)}
            y2={95 - 70 * Math.sin((Math.PI * (180 - angle)) / 180)}
            stroke="hsl(var(--foreground))"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
          <circle cx="100" cy="95" r="5" fill="hsl(var(--foreground))" />
        </svg>
      </div>
      <div className="text-center mt-2">
        <span className="text-3xl font-bold">{score.toFixed(2)}</span>
        <p className={`text-sm font-semibold ${labelColor}`}>{label}</p>
      </div>
    </div>
  );
}

const platformIcon = (platform: SentimentSource["platform"]) => {
  switch (platform) {
    case "twitter": return <Twitter className="h-4 w-4" />;
    case "reddit": return <MessageCircle className="h-4 w-4" />;
    case "yahoo": return <Newspaper className="h-4 w-4" />;
  }
};

const sentimentIcon = (sentiment: SentimentSource["sentiment"]) => {
  switch (sentiment) {
    case "positive": return <TrendingUp className="h-3.5 w-3.5 text-positive" />;
    case "negative": return <TrendingDown className="h-3.5 w-3.5 text-negative" />;
    case "neutral": return <Minus className="h-3.5 w-3.5 text-neutral" />;
  }
};

export function SentimentPanel({ loading }: SentimentPanelProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-6 h-full flex flex-col">
      <h3 className="text-base font-semibold mb-1">Sentiment Analysis</h3>
      <p className="text-xs text-muted-foreground mb-4">Aggregated from social & news sources</p>

      <SentimentGauge score={MOCK_SENTIMENT_SCORE} loading={loading} />

      <div className="mt-4 border-t border-border pt-4 flex-1">
        <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Recent Sources</h4>
        <div className="space-y-3">
          {loading
            ? Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="animate-pulse flex gap-3 items-start">
                  <div className="h-8 w-8 bg-muted rounded-full" />
                  <div className="flex-1 space-y-1.5">
                    <div className="h-3 w-24 bg-muted rounded" />
                    <div className="h-3 w-full bg-muted rounded" />
                  </div>
                </div>
              ))
            : MOCK_SOURCES.map((source, i) => (
                <div key={i} className="flex gap-3 items-start group">
                  <div className="mt-0.5 h-8 w-8 rounded-full bg-secondary flex items-center justify-center text-muted-foreground">
                    {platformIcon(source.platform)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium truncate">{source.name}</span>
                      {sentimentIcon(source.sentiment)}
                      <span className="text-xs text-muted-foreground ml-auto whitespace-nowrap">{source.time}</span>
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed mt-0.5 line-clamp-2">{source.snippet}</p>
                  </div>
                </div>
              ))}
        </div>
      </div>
    </div>
  );
}
