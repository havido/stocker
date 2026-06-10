import { ExternalLink, FileText } from "lucide-react";
import type { Source } from "@/components/SentimentResults";

interface SourcesListProps {
  sources: Source[];
}

/** Shows the actual articles/posts the sentiment grade was computed from. */
export function SourcesList({ sources }: SourcesListProps) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="rounded-xl border border-border bg-card p-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="flex items-center gap-2 mb-4">
        <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
          <FileText className="h-4 w-4 text-primary" />
        </div>
        <div>
          <h3 className="text-sm font-semibold">Sources</h3>
          <p className="text-xs text-muted-foreground">
            {sources.length} {sources.length === 1 ? "source" : "sources"} used for this grade
          </p>
        </div>
      </div>

      <ul className="space-y-1.5">
        {sources.map((s, i) => (
          <li key={`${s.url}-${i}`}>
            <a
              href={s.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group flex items-start gap-2.5 rounded-lg px-2 py-1.5 -mx-2 hover:bg-secondary/60 transition-colors"
            >
              <span
                className={`mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                  s.source === "reddit"
                    ? "bg-orange-500/10 text-orange-500"
                    : "bg-sky-500/10 text-sky-500"
                }`}
              >
                {s.source}
              </span>
              <span className="flex-1 text-sm text-foreground/90 line-clamp-2 group-hover:text-foreground">
                {s.title || s.url}
              </span>
              <ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
