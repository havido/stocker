import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Star, Check } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { apiPost } from "@/lib/api";
import { toast } from "sonner";

interface SaveToListButtonProps {
  ticker: string;
}

/** Small button to save the current ticker to the user's watchlist. */
export function SaveToListButton({ ticker }: SaveToListButtonProps) {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    if (!ticker) return;
    if (!isAuthenticated) {
      toast.error("Sign in to save tickers to your list");
      navigate("/login");
      return;
    }
    setSaving(true);
    try {
      await apiPost("/v1/users/watchlist", { ticker });
      setSaved(true);
      toast.success(`${ticker} saved to your list`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save ticker");
    } finally {
      setSaving(false);
    }
  };

  return (
    <button
      onClick={handleSave}
      disabled={saving || saved}
      className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all disabled:cursor-default ${
        saved
          ? "bg-primary/10 text-primary"
          : "bg-secondary text-muted-foreground hover:text-foreground hover:bg-secondary/80"
      }`}
    >
      {saved ? <Check className="h-4 w-4" /> : <Star className="h-4 w-4" />}
      {saved ? "Saved to list" : "Save to list"}
    </button>
  );
}
