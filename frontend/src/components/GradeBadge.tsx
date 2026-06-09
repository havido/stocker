import { TrendingUp, TrendingDown, ArrowUp, ArrowDown, Minus } from "lucide-react";

const GRADE_CONFIG: Record<string, {
  bg: string;
  text: string;
  glow: string;
  border: string;
  icon: React.ReactNode;
}> = {
  "Strong Buy": {
    bg: "bg-emerald-500/10",
    text: "text-emerald-500",
    glow: "shadow-emerald-500/20",
    border: "border-emerald-500/30",
    icon: <TrendingUp className="h-4 w-4" />,
  },
  "Buy": {
    bg: "bg-lime-500/10",
    text: "text-lime-500",
    glow: "shadow-lime-500/20",
    border: "border-lime-500/30",
    icon: <ArrowUp className="h-4 w-4" />,
  },
  "Hold": {
    bg: "bg-amber-500/10",
    text: "text-amber-500",
    glow: "shadow-amber-500/20",
    border: "border-amber-500/30",
    icon: <Minus className="h-4 w-4" />,
  },
  "Sell": {
    bg: "bg-orange-500/10",
    text: "text-orange-500",
    glow: "shadow-orange-500/20",
    border: "border-orange-500/30",
    icon: <ArrowDown className="h-4 w-4" />,
  },
  "Strong Sell": {
    bg: "bg-red-500/10",
    text: "text-red-500",
    glow: "shadow-red-500/20",
    border: "border-red-500/30",
    icon: <TrendingDown className="h-4 w-4" />,
  },
};

interface GradeBadgeProps {
  grade: string;
}

export function GradeBadge({ grade }: GradeBadgeProps) {
  const config = GRADE_CONFIG[grade] || GRADE_CONFIG["Hold"];

  return (
    <div
      className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-full border shadow-lg transition-all duration-300 ${config.bg} ${config.border} ${config.glow}`}
    >
      <span className={config.text}>{config.icon}</span>
      <span className={`text-sm font-bold uppercase tracking-wider ${config.text}`}>
        {grade}
      </span>
    </div>
  );
}
