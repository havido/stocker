import { useState, useCallback, useRef } from "react";
import { DashboardHeader } from "@/components/DashboardHeader";
import { SentimentResults, type SentimentData } from "@/components/SentimentResults";
import { WatchlistSidebar } from "@/components/WatchlistSidebar";
import { BarChart3, AlertCircle } from "lucide-react";

const API_BASE = "http://localhost:8000";
const POLL_INTERVAL_MS = 2000;

type AppState = "idle" | "loading" | "completed" | "error";

const Index = () => {
  const [ticker, setTicker] = useState("");
  const [activeTicker, setActiveTicker] = useState("");
  const [appState, setAppState] = useState<AppState>("idle");
  const [sentimentData, setSentimentData] = useState<SentimentData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [watchlistOpen, setWatchlistOpen] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const pollForResult = useCallback((taskId: string) => {
    stopPolling();

    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/status/${taskId}`);
        if (!res.ok) throw new Error(`Status check failed (${res.status})`);
        const data = await res.json();

        if (data.status === "completed") {
          stopPolling();
          setSentimentData(data.result);
          setAppState("completed");
        } else if (data.status === "failed") {
          stopPolling();
          setError(data.error || "Analysis failed. Please try again.");
          setAppState("error");
        }
        // If still "processing", keep polling
      } catch (err) {
        stopPolling();
        setError(err instanceof Error ? err.message : "Something went wrong");
        setAppState("error");
      }
    }, POLL_INTERVAL_MS);
  }, []);

  const handleSearch = useCallback(async () => {
    const cleanTicker = ticker.replace("$", "").trim();
    if (!cleanTicker) return;

    stopPolling();
    setActiveTicker(cleanTicker);
    setSentimentData(null);
    setError(null);
    setAppState("loading");

    try {
      const res = await fetch(`${API_BASE}/api/ticker`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: cleanTicker }),
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      const data = await res.json();

      if (data.status === "hit" && data.data) {
        setSentimentData(data.data);
        setAppState("completed");
      } else if (data.task_id) {
        pollForResult(data.task_id);
      } else {
        throw new Error("No task ID returned from server");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start analysis");
      setAppState("error");
    }
  }, [ticker, pollForResult]);

  const handleSelectTicker = (t: string) => {
    setTicker(t);
    setWatchlistOpen(false);
    // Trigger search for selected ticker
    const cleanTicker = t.replace("$", "").trim();
    if (!cleanTicker) return;

    stopPolling();
    setActiveTicker(cleanTicker);
    setSentimentData(null);
    setError(null);
    setAppState("loading");

    fetch(`${API_BASE}/api/ticker`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker: cleanTicker }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed (${res.status})`);
        return res.json();
      })
      .then((data) => {
        if (data.status === "hit" && data.data) {
          setSentimentData(data.data);
          setAppState("completed");
        } else if (data.task_id) {
          pollForResult(data.task_id);
        } else {
          throw new Error("No task ID returned from server");
        }
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to start analysis");
        setAppState("error");
      });
  };

  return (
    <div className="min-h-screen bg-background">
      <DashboardHeader
        ticker={ticker}
        onTickerChange={setTicker}
        onSearch={handleSearch}
        onToggleWatchlist={() => setWatchlistOpen((v) => !v)}
        loading={appState === "loading"}
      />

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* Scanning state banner */}
        {appState === "loading" && (
          <div className="flex items-center gap-3 rounded-lg bg-primary/5 border border-primary/20 px-4 py-3 animate-in fade-in duration-300">
            <div className="h-4 w-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span className="text-sm font-medium text-primary">
              Scanning &amp; Analyzing <span className="font-bold">${activeTicker}</span>
              <span className="text-muted-foreground ml-2 text-xs">This may take a moment...</span>
            </span>
          </div>
        )}

        {/* Error state */}
        {appState === "error" && error && (
          <div className="flex items-center gap-3 rounded-lg bg-negative/5 border border-negative/20 px-4 py-3 animate-in fade-in duration-300">
            <AlertCircle className="h-4 w-4 text-negative flex-shrink-0" />
            <span className="text-sm font-medium text-negative">{error}</span>
          </div>
        )}

        {/* Idle state — empty prompt */}
        {appState === "idle" && (
          <div className="flex flex-col items-center justify-center py-24 text-center animate-in fade-in duration-500">
            <div className="h-20 w-20 rounded-2xl bg-primary/10 flex items-center justify-center mb-6">
              <BarChart3 className="h-10 w-10 text-primary" />
            </div>
            <h2 className="text-2xl font-bold mb-2">Stock Sentiment Analyzer</h2>
            <p className="text-muted-foreground max-w-md mb-6">
              Enter a stock ticker above to analyze sentiment from Reddit and news sources using FinBERT AI.
            </p>
            <div className="flex gap-2">
              {["AAPL", "TSLA", "NVDA", "MSFT"].map((t) => (
                <button
                  key={t}
                  onClick={() => {
                    setTicker(t);
                    handleSelectTicker(t);
                  }}
                  className="px-4 py-2 rounded-lg bg-secondary text-sm font-semibold text-muted-foreground hover:text-foreground hover:bg-secondary/80 transition-all"
                >
                  ${t}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Results */}
        {appState === "completed" && sentimentData && (
          <SentimentResults data={sentimentData} ticker={activeTicker} />
        )}
      </main>

      <WatchlistSidebar
        open={watchlistOpen}
        onClose={() => setWatchlistOpen(false)}
        onSelectTicker={handleSelectTicker}
      />
    </div>
  );
};

export default Index;
