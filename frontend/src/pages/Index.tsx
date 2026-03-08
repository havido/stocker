import { useState, useCallback } from "react";
import { DashboardHeader } from "@/components/DashboardHeader";
import { StockChart } from "@/components/StockChart";
import { SentimentPanel } from "@/components/SentimentPanel";
import { CorrelationTable } from "@/components/CorrelationTable";
import { WatchlistSidebar } from "@/components/WatchlistSidebar";
import { MOCK_STOCK, type StockData } from "@/lib/mockData";

const Index = () => {
  const [ticker, setTicker] = useState("AAPL");
  const [stock, setStock] = useState<StockData>(MOCK_STOCK);
  const [loading, setLoading] = useState(false);
  const [watchlistOpen, setWatchlistOpen] = useState(false);

  const handleSearch = useCallback(() => {
    if (!ticker.trim()) return;
    setLoading(true);
    // Simulate API call
    setTimeout(() => {
      setStock({
        ...MOCK_STOCK,
        ticker: ticker.replace("$", ""),
        price: MOCK_STOCK.price + (Math.random() - 0.5) * 20,
        change: (Math.random() - 0.3) * 5,
        changePercent: (Math.random() - 0.3) * 4,
      });
      setLoading(false);
    }, 1500);
  }, [ticker]);

  const handleSelectTicker = (t: string) => {
    setTicker(t);
    setWatchlistOpen(false);
    setLoading(true);
    setTimeout(() => {
      setStock({
        ...MOCK_STOCK,
        ticker: t,
        price: MOCK_STOCK.price + (Math.random() - 0.5) * 20,
        change: (Math.random() - 0.3) * 5,
        changePercent: (Math.random() - 0.3) * 4,
      });
      setLoading(false);
    }, 1500);
  };

  return (
    <div className="min-h-screen bg-background">
      <DashboardHeader
        ticker={ticker}
        onTickerChange={setTicker}
        onSearch={handleSearch}
        onToggleWatchlist={() => setWatchlistOpen((v) => !v)}
        loading={loading}
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* Scanning state banner */}
        {loading && (
          <div className="flex items-center gap-3 rounded-lg bg-primary/5 border border-primary/20 px-4 py-3">
            <div className="h-4 w-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span className="text-sm font-medium text-primary">
              Scanning & Analyzing <span className="font-bold">${ticker.replace("$", "")}</span>...
            </span>
          </div>
        )}

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <div className="lg:col-span-3">
            <StockChart stock={stock} loading={loading} />
          </div>
          <div className="lg:col-span-2">
            <SentimentPanel loading={loading} />
          </div>
        </div>

        {/* Bottom section */}
        <CorrelationTable loading={loading} />
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
