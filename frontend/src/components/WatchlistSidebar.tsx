import { useState, useEffect } from "react";
import { X, TrendingUp, TrendingDown, Plus, Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/context/AuthContext";
import { apiGet, apiPost, apiDelete } from "@/lib/api";
import { toast } from "sonner";

interface WatchlistItem {
  ticker: string;
  added_at: string;
}

interface WatchlistSidebarProps {
  open: boolean;
  onClose: () => void;
  onSelectTicker: (ticker: string) => void;
}

export function WatchlistSidebar({ open, onClose, onSelectTicker }: WatchlistSidebarProps) {
  const { isAuthenticated } = useAuth();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [addTicker, setAddTicker] = useState("");

  useEffect(() => {
    if (open && isAuthenticated) {
      setLoading(true);
      apiGet("/v1/users/watchlist")
        .then((data) => setItems(data.items || []))
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [open, isAuthenticated]);

  const handleAdd = async () => {
    const ticker = addTicker.replace("$", "").trim().toUpperCase();
    if (!ticker) return;
    try {
      await apiPost("/v1/users/watchlist", { ticker });
      setItems((prev) => [{ ticker, added_at: new Date().toISOString() }, ...prev]);
      setAddTicker("");
      toast.success(`${ticker} added`);
    } catch {
      toast.error("Failed to add ticker");
    }
  };

  const handleRemove = async (ticker: string) => {
    try {
      await apiDelete(`/v1/users/watchlist/${ticker}`);
      setItems((prev) => prev.filter((i) => i.ticker !== ticker));
    } catch {
      toast.error("Failed to remove ticker");
    }
  };

  return (
    <>
      {/* Overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-foreground/10 backdrop-blur-sm z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed right-0 top-0 h-full w-80 bg-card border-l border-border z-50 transform transition-transform duration-300 ease-in-out ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between p-5 border-b border-border">
          <h3 className="text-base font-semibold">Watchlist</h3>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {isAuthenticated ? (
          <>
            {/* Quick add */}
            <div className="p-4 border-b border-border">
              <div className="flex gap-2">
                <Input
                  placeholder="Add ticker..."
                  value={addTicker}
                  onChange={(e) => setAddTicker(e.target.value.toUpperCase())}
                  onKeyDown={(e) => e.key === "Enter" && handleAdd()}
                  className="bg-secondary/50 text-sm"
                />
                <Button size="icon" variant="secondary" onClick={handleAdd}>
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="p-4 space-y-1 overflow-y-auto max-h-[calc(100vh-180px)]">
              {loading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="animate-pulse flex items-center justify-between p-3">
                    <div className="space-y-1.5">
                      <div className="h-4 w-16 bg-muted rounded" />
                      <div className="h-3 w-24 bg-muted rounded" />
                    </div>
                    <div className="h-4 w-12 bg-muted rounded" />
                  </div>
                ))
              ) : items.length === 0 ? (
                <div className="text-center py-8">
                  <Star className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">No tickers saved yet</p>
                </div>
              ) : (
                items.map((item) => (
                  <div key={item.ticker} className="group flex items-center justify-between">
                    <button
                      onClick={() => onSelectTicker(item.ticker)}
                      className="flex-1 flex items-center justify-between p-3 rounded-lg hover:bg-secondary/70 transition-colors text-left"
                    >
                      <div>
                        <span className="text-sm font-semibold">${item.ticker}</span>
                        <p className="text-xs text-muted-foreground">
                          {new Date(item.added_at).toLocaleDateString()}
                        </p>
                      </div>
                    </button>
                    <button
                      onClick={() => handleRemove(item.ticker)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 mr-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </>
        ) : (
          <div className="p-8 text-center">
            <Star className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">
              Sign in to save tickers to your watchlist
            </p>
          </div>
        )}
      </aside>
    </>
  );
}
