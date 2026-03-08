import { useState, useCallback, useRef } from "react";
import { DashboardHeader } from "@/components/DashboardHeader";
import { SentimentResults, type SentimentData } from "@/components/SentimentResults";
import { StockChart, type StockChartData } from "@/components/StockChart";
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
  const [stockData, setStockData] = useState<StockChartData | null>(null);
  const [stockLoading, setStockLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [watchlistOpen, setWatchlistOpen] = useState(false);
  const [logs, setLogs] = useState<{ step: string, message: string }[]>([]);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const streamRef = useRef<EventSource | null>(null);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.close();
      streamRef.current = null;
    }
  };

  const fetchStockData = useCallback(async (cleanTicker: string) => {
    setStockLoading(true);
    setStockData(null);
    try {
      const res = await fetch(`${API_BASE}/api/stock/${cleanTicker}`);
      if (!res.ok) throw new Error(`Stock data fetch failed (${res.status})`);
      const data = await res.json();
      setStockData(data);
    } catch {
      setStockData(null);
    } finally {
      setStockLoading(false);
    }
  }, []);

  const streamForResult = useCallback((taskId: string) => {
    stopPolling();

    const es = new EventSource(`${API_BASE}/api/stream/${taskId}`);
    streamRef.current = es;

    es.onmessage = async (event) => {
      if (event.data === "DONE") {
        es.close();
        streamRef.current = null;

        // Fetch the final result
        try {
          const res = await fetch(`${API_BASE}/api/status/${taskId}`);
          const data = await res.json();
          if (data.status === "completed") {
            setSentimentData(data.result);
            setAppState("completed");
            setLogs([]); // Clear logs when done
          } else {
            setError("Analysis failed. Please try again.");
            setAppState("error");
          }
        } catch (err) {
          setError("Failed to fetch final results");
          setAppState("error");
        }
      } else {
        // new log
        try {
          const parsed = JSON.parse(event.data);
          if (parsed && parsed.step && parsed.message) {
            setLogs((prev) => {
              const filtered = prev.filter(l => l.step !== parsed.step);
              return [...filtered, parsed];
            });
          }
        } catch (e) {
          console.warn("Unparseable log", event.data);
        }
      }
    };

    es.onerror = (err) => {
      es.close();
      streamRef.current = null;
      setError("Stream connection lost");
      setAppState("error");
    };
  }, []);

  const startSearch = useCallback(
    async (cleanTicker: string) => {
      stopPolling();
      setActiveTicker(cleanTicker);
      setSentimentData(null);
      setError(null);
      setLogs([]);
      setAppState("loading");

      fetchStockData(cleanTicker);

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
          streamForResult(data.task_id);
        } else {
          throw new Error("No task ID returned from server");
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to start analysis");
        setAppState("error");
      }
    },
    [fetchStockData, streamForResult]
  );

  const handleSearch = useCallback(async () => {
    const cleanTicker = ticker.replace("$", "").trim().toUpperCase();
    if (!cleanTicker) return;
    await startSearch(cleanTicker);
  }, [ticker, startSearch]);

  const handleSelectTicker = useCallback(
    (t: string) => {
      const cleanTicker = t.replace("$", "").trim().toUpperCase();
      if (!cleanTicker) return;
      setTicker(cleanTicker);
      setWatchlistOpen(false);
      startSearch(cleanTicker);
    },
    [startSearch]
  );

  const showResults = appState !== "idle";

  return (
    <div className="min-h-screen bg-background">
      <DashboardHeader
        ticker={ticker}
        onTickerChange={setTicker}
        onSearch={handleSearch}
        onToggleWatchlist={() => setWatchlistOpen((v) => !v)}
        loading={appState === "loading"}
      />

      <main className="max-w-[1400px] mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* Idle state — empty prompt */}
        {appState === "idle" && (
          <div className="flex flex-col items-center justify-center py-24 text-center animate-in fade-in duration-500">
            <div className="h-20 w-20 rounded-2xl bg-primary/10 flex items-center justify-center mb-6">
              <BarChart3 className="h-10 w-10 text-primary" />
            </div>
            <h2 className="text-2xl font-bold mb-2">Stock Sentiment Analyzer</h2>
            <p className="text-muted-foreground max-w-md mb-6">
              Enter a stock ticker above to see the price chart and analyze sentiment from Reddit
              and news sources using FinBERT AI.
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

        {/* Side-by-side results layout */}
        {showResults && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 animate-in fade-in duration-300">
            {/* Left — Stock Chart */}
            <div>
              <StockChart data={stockData} loading={stockLoading} />
            </div>

            {/* Right — Sentiment Panel */}
            <div className="space-y-4">
              {/* Scanning banner */}
              {appState === "loading" && (
                <div className="flex flex-col gap-3 rounded-lg bg-primary/5 border border-primary/20 px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className="h-4 w-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    <span className="text-sm font-medium text-primary">
                      Scanning &amp; Analyzing{" "}
                      <span className="font-bold">${activeTicker}</span>
                      <span className="text-muted-foreground ml-2 text-xs">
                        This may take a moment...
                      </span>
                    </span>
                  </div>
                  {/* Logs stream */}
                  {logs.length > 0 && (
                    <div className="flex flex-col gap-1 border-t border-primary/10 pt-2 w-full">
                      {logs.map((log) => (
                        <span key={log.step} className="text-xs text-gray-500 animate-in fade-in duration-300">
                          {log.message}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Error state */}
              {appState === "error" && error && (
                <div className="flex items-center gap-3 rounded-lg bg-negative/5 border border-negative/20 px-4 py-3">
                  <AlertCircle className="h-4 w-4 text-negative flex-shrink-0" />
                  <span className="text-sm font-medium text-negative">{error}</span>
                </div>
              )}

              {/* Sentiment results */}
              {appState === "completed" && sentimentData && (
                <SentimentResults data={sentimentData} ticker={activeTicker} />
              )}
            </div>
          </div>
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
