import { useNavigate } from "react-router-dom";
import { Search, Star, User, Moon, Sun, LogIn, LogOut, LayoutDashboard } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTheme } from "@/hooks/useTheme";
import { useAuth } from "@/context/AuthContext";

interface DashboardHeaderProps {
  ticker: string;
  onTickerChange: (ticker: string) => void;
  onSearch: () => void;
  onToggleWatchlist: () => void;
  loading: boolean;
}

export function DashboardHeader({ ticker, onTickerChange, onSearch, onToggleWatchlist, loading }: DashboardHeaderProps) {
  const { theme, toggleTheme } = useTheme();
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") onSearch();
  };

  return (
    <header className="flex items-center justify-between gap-4 border-b border-border px-6 py-4">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate("/")} className="flex items-center gap-1">
          <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-sm">SP</span>
          </div>
          <span className="text-lg font-semibold tracking-tight">Stockr</span>
        </button>
      </div>

      <div className="flex-1 max-w-xl">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={ticker}
            onChange={(e) => onTickerChange(e.target.value.toUpperCase())}
            onKeyDown={handleKeyDown}
            placeholder="Search ticker (e.g. $AAPL)"
            className="w-full rounded-lg border border-input bg-secondary/50 py-2.5 pl-10 pr-4 text-sm font-medium placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-all"
          />
          {loading && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <div className="h-4 w-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label="Toggle theme">
          {theme === "light" ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
        </Button>
        <Button variant="outline" size="sm" onClick={onToggleWatchlist} className="gap-2">
          <Star className="h-4 w-4" />
          Watchlist
        </Button>

        {isAuthenticated ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="User menu">
                <User className="h-5 w-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <div className="px-2 py-1.5">
                <p className="text-sm font-medium truncate">{user?.email}</p>
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => navigate("/dashboard")} className="gap-2 cursor-pointer">
                <LayoutDashboard className="h-4 w-4" />
                Dashboard
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={logout} className="gap-2 cursor-pointer text-destructive focus:text-destructive">
                <LogOut className="h-4 w-4" />
                Sign Out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : (
          <Button variant="ghost" size="sm" className="gap-2" onClick={() => navigate("/login")}>
            <LogIn className="h-4 w-4" />
            Sign In
          </Button>
        )}
      </div>
    </header>
  );
}
