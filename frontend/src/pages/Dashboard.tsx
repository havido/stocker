import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { apiGet, apiPost, apiDelete } from "@/lib/api";
import { DashboardHeader } from "@/components/DashboardHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Star, Plus, Trash2, TrendingUp, Search } from "lucide-react";
import { toast } from "sonner";

interface WatchlistItem {
  ticker: string;
  added_at: string;
}

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [addTicker, setAddTicker] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const [adding, setAdding] = useState(false);

  const fetchWatchlist = async () => {
    try {
      const data = await apiGet("/v1/users/watchlist");
      setItems(data.items || []);
    } catch {
      // Non-fatal — user may not have items
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWatchlist();
  }, []);

  const handleAdd = async () => {
    const ticker = addTicker.replace("$", "").trim().toUpperCase();
    if (!ticker) return;

    setAdding(true);
    try {
      await apiPost("/v1/users/watchlist", { ticker });
      toast.success(`${ticker} added to watchlist`);
      setAddTicker("");
      setAddOpen(false);
      fetchWatchlist();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add ticker");
    } finally {
      setAdding(false);
    }
  };

  const handleRemove = async (ticker: string) => {
    try {
      await apiDelete(`/v1/users/watchlist/${ticker}`);
      setItems((prev) => prev.filter((i) => i.ticker !== ticker));
      toast.success(`${ticker} removed`);
    } catch {
      toast.error("Failed to remove ticker");
    }
  };

  const handleAnalyze = (ticker: string) => {
    navigate(`/?ticker=${ticker}`);
  };

  return (
    <div className="min-h-screen bg-background">
      <DashboardHeader
        ticker=""
        onTickerChange={() => {}}
        onSearch={() => {}}
        onToggleWatchlist={() => {}}
        loading={false}
      />

      <main className="max-w-[1200px] mx-auto px-4 sm:px-6 py-8">
        {/* Page header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold">Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Welcome back, {user?.email?.split("@")[0] || "investor"}
            </p>
          </div>

          <Dialog open={addOpen} onOpenChange={setAddOpen}>
            <DialogTrigger asChild>
              <Button size="sm" className="gap-2">
                <Plus className="h-4 w-4" />
                Add Ticker
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[360px]">
              <DialogHeader>
                <DialogTitle>Add to Watchlist</DialogTitle>
                <DialogDescription>
                  Enter a stock ticker to track.
                </DialogDescription>
              </DialogHeader>
              <div className="flex gap-2 mt-2">
                <Input
                  placeholder="e.g. AAPL"
                  value={addTicker}
                  onChange={(e) => setAddTicker(e.target.value.toUpperCase())}
                  onKeyDown={(e) => e.key === "Enter" && handleAdd()}
                  autoFocus
                  className="bg-secondary/50"
                />
                <Button onClick={handleAdd} disabled={adding}>
                  {adding ? (
                    <div className="h-4 w-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                  ) : (
                    "Add"
                  )}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {/* Watchlist grid */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i} className="animate-pulse">
                <CardContent className="p-5 space-y-3">
                  <div className="h-5 w-20 bg-muted rounded" />
                  <div className="h-3 w-32 bg-muted rounded" />
                  <div className="h-8 w-full bg-muted rounded" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="h-16 w-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
              <Star className="h-8 w-8 text-primary" />
            </div>
            <h2 className="text-xl font-semibold mb-2">Your watchlist is empty</h2>
            <p className="text-sm text-muted-foreground max-w-sm mb-4">
              Search for a ticker and click the star to save it, or add one directly.
            </p>
            <Button size="sm" className="gap-2" onClick={() => setAddOpen(true)}>
              <Plus className="h-4 w-4" />
              Add Your First Ticker
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {items.map((item) => (
              <Card
                key={item.ticker}
                className="group hover:shadow-lg hover:shadow-primary/5 transition-all duration-300 border-border/50"
              >
                <CardContent className="p-5">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
                        <TrendingUp className="h-4 w-4 text-primary" />
                      </div>
                      <span className="text-lg font-bold">${item.ticker}</span>
                    </div>
                    <button
                      onClick={() => handleRemove(item.ticker)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg hover:bg-destructive/10 text-muted-foreground hover:text-destructive"
                      title="Remove from watchlist"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>

                  <p className="text-xs text-muted-foreground mb-4">
                    Added {new Date(item.added_at).toLocaleDateString()}
                  </p>

                  <Button
                    variant="secondary"
                    size="sm"
                    className="w-full gap-2"
                    onClick={() => handleAnalyze(item.ticker)}
                  >
                    <Search className="h-3.5 w-3.5" />
                    Analyze Sentiment
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
