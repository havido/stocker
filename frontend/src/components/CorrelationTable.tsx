import { MOCK_CORRELATIONS } from "@/lib/mockData";

interface CorrelationTableProps {
  loading: boolean;
}

export function CorrelationTable({ loading }: CorrelationTableProps) {
  if (loading) {
    return (
      <div className="rounded-xl border border-border bg-card p-6 animate-pulse space-y-3">
        <div className="h-5 w-48 bg-muted rounded" />
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-12 bg-muted rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <h3 className="text-base font-semibold mb-1">Correlation Analysis</h3>
      <p className="text-xs text-muted-foreground mb-4">Sentiment-price correlation powered by finBERT</p>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2.5 font-semibold text-muted-foreground text-xs uppercase tracking-wider">Factor</th>
              <th className="text-center py-2.5 font-semibold text-muted-foreground text-xs uppercase tracking-wider w-24">r Score</th>
              <th className="text-left py-2.5 font-semibold text-muted-foreground text-xs uppercase tracking-wider">AI Reasoning</th>
            </tr>
          </thead>
          <tbody>
            {MOCK_CORRELATIONS.map((entry, i) => (
              <tr key={i} className="border-b border-border last:border-0 hover:bg-secondary/50 transition-colors">
                <td className="py-3 font-medium">{entry.factor}</td>
                <td className="py-3 text-center">
                  <span
                    className={`inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-xs font-bold ${
                      entry.rScore >= 0.7
                        ? "bg-positive/10 text-positive"
                        : entry.rScore >= 0.4
                        ? "bg-neutral/10 text-neutral"
                        : "bg-negative/10 text-negative"
                    }`}
                  >
                    {entry.rScore.toFixed(2)}
                  </span>
                </td>
                <td className="py-3 text-muted-foreground text-xs leading-relaxed">{entry.reasoning}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
