import { useState, useCallback, useRef, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { DashboardHeader } from "@/components/DashboardHeader";
import { SentimentResults, type SentimentData } from "@/components/SentimentResults";
import { StockChart, type StockChartData } from "@/components/StockChart";
import { WatchlistSidebar } from "@/components/WatchlistSidebar";
import { AISummary } from "@/components/AISummary";
import { BarChart3, AlertCircle } from "lucide-react";
import { API_BASE } from "@/lib/api";
import { normalizeTicker, isValidTickerShape } from "@/lib/ticker";

type AppState = "idle" | "loading" | "completed" | "error";

const Index = () => {
  const [searchParams] = useSearchParams();
  const [ticker, setTicker] = useState("");
  const [activeTicker, setActiveTicker] = useState("");
  const [appState, setAppState] = useState<AppState>("idle");
  const [sentimentData, setSentimentData] = useState<SentimentData | null>(null);
  const [stockData, setStockData] = useState<StockChartData | null>(null);
  const [stockLoading, setStockLoading] = useState(false);
  const [stockError, setStockError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [watchlistOpen, setWatchlistOpen] = useState(false);
  const [logs, setLogs] = useState<{ step: string; message: string }[]>([]);
  const [aiSummary, setAiSummary] = useState("");
  const streamRef = useRef<EventSource | null>(null);

  const stopStream = () => {
    if (streamRef.current) {
      streamRef.current.close();
      streamRef.current = null;
    }
  };

  const fetchStockData = useCallback(async (cleanTicker: string) => {
    setStockLoading(true);
    setStockData(null);
    setStockError(null);
    try {
      const res = await fetch(`${API_BASE}/v1/stocks/${cleanTicker}/chart`);
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Couldn't load market data (${res.status})`);
      }
      const data = await res.json();
      setStockData(data);
    } catch (err) {
      setStockData(null);
      setStockError(err instanceof Error ? err.message : "Couldn't load market data");
    } finally {
      setStockLoading(false);
    }
  }, []);

  const streamForResult = useCallback((taskId: string) => {
    stopStream();

    const es = new EventSource(`${API_BASE}/v1/analysis/jobs/${taskId}/stream`);
    streamRef.current = es;

    // Captured from "error"/"timeout" log lines so the terminal ERROR sentinel
    // can show a meaningful reason rather than a generic message.
    let failureMessage = "";

    const fail = (message: string) => {
      es.close();
      streamRef.current = null;
      setError(message);
      setAppState("error");
    };

    es.onmessage = async (event) => {
      if (event.data === "DONE") {
        es.close();
        streamRef.current = null;

        // Fetch the final result
        try {
          const res = await fetch(`${API_BASE}/v1/analysis/jobs/${taskId}`);
          const data = await res.json();
          if (data.status === "completed") {
            setSentimentData(data.result);
            setAiSummary(data.result?.ai_summary || "");
            setAppState("completed");
            setLogs([]);
          } else {
            fail("Analysis finished but no result was returned. Please try again.");
          }
        } catch {
          fail("Failed to fetch final results");
        }
        return;
      }

      if (event.data === "ERROR") {
        // Terminal failure from the worker (or stream timeout).
        fail(failureMessage || "Analysis failed. Please try again.");
        return;
      }

      try {
        const parsed = JSON.parse(event.data);
        if (parsed && (parsed.step === "error" || parsed.step === "timeout")) {
          // Remember the reason; the ERROR sentinel will follow and end the stream.
          failureMessage = parsed.message || failureMessage;
        } else if (parsed && parsed.step && parsed.message) {
          setLogs((prev) => {
            const filtered = prev.filter((l) => l.step !== parsed.step);
            return [...filtered, parsed];
          });
        }
      } catch {
        console.warn("Unparseable log", event.data);
      }
    };

    es.onerror = () => {
      es.close();
      streamRef.current = null;
      // Only surface a connection error if we weren't already done.
      setAppState((s) => (s === "completed" ? s : "error"));
      setError((e) => e || "Connection to the analysis stream was lost");
    };
  }, []);

  const startSearch = useCallback(
    async (cleanTicker: string) => {
      stopStream();
      setActiveTicker(cleanTicker);
      setSentimentData(null);
      setAiSummary("");
      setError(null);
      setLogs([]);
      setAppState("loading");

      fetchStockData(cleanTicker);

      try {
        const res = await fetch(`${API_BASE}/v1/analysis/jobs`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ticker: cleanTicker }),
        });
        if (!res.ok) {
          // Surface the server's message (e.g. "'ASDFGH' is not a recognized ticker")
          const body = await res.json().catch(() => null);
          throw new Error(body?.detail || `Request failed (${res.status})`);
        }
        const data = await res.json();

        if (data.status === "hit" && data.data) {
          setSentimentData(data.data);
          setAiSummary(data.data?.ai_summary || "");
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
    const cleanTicker = normalizeTicker(ticker);
    if (!cleanTicker) return;
    // Block obviously-malformed input before the round-trip; the backend still
    // does the authoritative existence check.
    if (!isValidTickerShape(cleanTicker)) {
      setActiveTicker(cleanTicker);
      setError(`'${cleanTicker}' is not a valid ticker symbol`);
      setAppState("error");
      return;
    }
    await startSearch(cleanTicker);
  }, [ticker, startSearch]);

  const handleSelectTicker = useCallback(
    (t: string) => {
      const cleanTicker = normalizeTicker(t);
      if (!cleanTicker) return;
      setTicker(cleanTicker);
      setWatchlistOpen(false);
      startSearch(cleanTicker);
    },
    [startSearch]
  );

  // Handle ?ticker= query param (from Dashboard navigation)
  useEffect(() => {
    const paramTicker = searchParams.get("ticker");
    if (paramTicker) {
      const clean = paramTicker.replace("$", "").trim().toUpperCase();
      if (clean && clean !== activeTicker) {
        setTicker(clean);
        startSearch(clean);
      }
    }
  }, [searchParams]); // eslint-disable-line react-hooks/exhaustive-deps

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
              <StockChart
                data={stockData}
                loading={stockLoading}
                error={stockError}
                onRetry={() => activeTicker && fetchStockData(activeTicker)}
              />
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
                  {/* Streaming logs */}
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

              {/* Completed with no articles — explicit empty state */}
              {appState === "completed" &&
                sentimentData &&
                sentimentData.positive + sentimentData.negative + sentimentData.neutral === 0 && (
                  <div className="flex items-center gap-3 rounded-lg bg-neutral/5 border border-neutral/20 px-4 py-3">
                    <AlertCircle className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <span className="text-sm font-medium text-muted-foreground">
                      No recent articles found for{" "}
                      <span className="font-bold">${activeTicker}</span>. Try again later or
                      pick another ticker.
                    </span>
                  </div>
                )}

              {/* Sentiment results + AI Summary */}
              {appState === "completed" &&
                sentimentData &&
                sentimentData.positive + sentimentData.negative + sentimentData.neutral > 0 && (
                  <>
                    <SentimentResults data={sentimentData} ticker={activeTicker} />
                    {aiSummary && <AISummary summary={aiSummary} ticker={activeTicker} />}
                  </>
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
