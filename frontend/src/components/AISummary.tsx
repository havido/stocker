import { Sparkles } from "lucide-react";

interface AISummaryProps {
  summary: string;
  ticker: string;
}

/** Simple inline markdown renderer — handles **bold**, ## headers, and - bullets. */
function renderMarkdown(text: string) {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];

  lines.forEach((line, i) => {
    const trimmed = line.trim();
    if (!trimmed) {
      elements.push(<div key={i} className="h-2" />);
    } else if (trimmed.startsWith("## ")) {
      elements.push(
        <h3 key={i} className="text-sm font-bold mt-3 mb-1 text-foreground">
          {trimmed.slice(3)}
        </h3>
      );
    } else if (trimmed.startsWith("# ")) {
      elements.push(
        <h2 key={i} className="text-base font-bold mt-3 mb-1 text-foreground">
          {trimmed.slice(2)}
        </h2>
      );
    } else if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      const content = trimmed.slice(2);
      elements.push(
        <li key={i} className="text-sm text-muted-foreground ml-4 list-disc leading-relaxed">
          {renderInline(content)}
        </li>
      );
    } else {
      elements.push(
        <p key={i} className="text-sm text-muted-foreground leading-relaxed">
          {renderInline(trimmed)}
        </p>
      );
    }
  });

  return elements;
}

/** Handle **bold** spans within a line. */
function renderInline(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <span key={i} className="font-semibold text-foreground">
          {part.slice(2, -2)}
        </span>
      );
    }
    return part;
  });
}

export function AISummary({ summary, ticker }: AISummaryProps) {
  if (!summary) return null;

  return (
    <div className="rounded-xl border border-border/50 bg-card/80 backdrop-blur-sm p-6 animate-in fade-in slide-in-from-bottom-2 duration-500 relative overflow-hidden">
      {/* Subtle gradient border effect */}
      <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-primary/5 via-transparent to-primary/5 pointer-events-none" />

      <div className="relative z-10">
        <div className="flex items-center gap-2 mb-4">
          <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
            <Sparkles className="h-4 w-4 text-primary" />
          </div>
          <div>
            <h3 className="text-sm font-semibold">AI Investment Summary</h3>
            <p className="text-xs text-muted-foreground">${ticker}</p>
          </div>
        </div>

        <div className="space-y-0.5">{renderMarkdown(summary)}</div>

        <div className="flex items-center gap-1.5 mt-5 pt-3 border-t border-border/50">
          <Sparkles className="h-3 w-3 text-muted-foreground" />
          <span className="text-[11px] text-muted-foreground">
            Powered by Llama 3.3 · Groq
          </span>
        </div>
      </div>
    </div>
  );
}
