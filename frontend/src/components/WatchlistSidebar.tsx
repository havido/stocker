import { X, TrendingUp, TrendingDown } from "lucide-react";
import { MOCK_WATCHLIST } from "@/lib/mockData";
import { Button } from "@/components/ui/button";

interface WatchlistSidebarProps {
  open: boolean;
  onClose: () => void;
  onSelectTicker: (ticker: string) => void;
}

export function WatchlistSidebar({ open, onClose, onSelectTicker }: WatchlistSidebarProps) {
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

        <div className="p-4 space-y-1">
          {MOCK_WATCHLIST.map((item) => {
            const isPositive = item.change >= 0;
            return (
              <button
                key={item.ticker}
                onClick={() => onSelectTicker(item.ticker)}
                className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-secondary/70 transition-colors text-left"
              >
                <div>
                  <span className="text-sm font-semibold">{item.ticker}</span>
                  <p className="text-xs text-muted-foreground">{item.name}</p>
                </div>
                <div className="text-right">
                  <span className="text-sm font-semibold">${item.price.toFixed(2)}</span>
                  <p className={`text-xs font-medium flex items-center justify-end gap-0.5 ${isPositive ? "text-positive" : "text-negative"}`}>
                    {isPositive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                    {isPositive ? "+" : ""}{item.change.toFixed(2)}%
                  </p>
                </div>
              </button>
            );
          })}
        </div>

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-border">
          <p className="text-xs text-muted-foreground text-center">
            Connect to Lovable Cloud to save your watchlist
          </p>
        </div>
      </aside>
    </>
  );
}
