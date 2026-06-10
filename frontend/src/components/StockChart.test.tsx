import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StockChart, type StockChartData } from "@/components/StockChart";

const data: StockChartData = {
  ticker: "AAPL",
  name: "Apple Inc.",
  price: 200,
  change: 2,
  changePercent: 1,
  history: { "1D": [{ time: "09:30", price: 200 }] },
};

describe("StockChart periods", () => {
  it("renders exactly the spec period buttons (1D, 1M, 6M, YTD, 1Y, 5Y, 10Y)", () => {
    render(<StockChart data={data} loading={false} />);
    for (const p of ["1D", "1M", "6M", "YTD", "1Y", "5Y", "10Y"]) {
      expect(screen.getByRole("button", { name: p })).toBeInTheDocument();
    }
  });

  it("no longer renders the removed 1W / ALL periods", () => {
    render(<StockChart data={data} loading={false} />);
    expect(screen.queryByRole("button", { name: "1W" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "ALL" })).not.toBeInTheDocument();
  });
});

describe("StockChart gain/loss", () => {
  // current 1000. Backend "today" = -0.50% (vs prev close 1005). The 1D chart
  // *opened* at 990 (intraday would be +1.01%). 10Y opened at 100 (+900%).
  const nvda: StockChartData = {
    ticker: "NVDA",
    name: "NVIDIA",
    price: 1000,
    change: -5, // current 1000 vs previous close 1005 → broker's "today"
    changePercent: -0.5,
    history: {
      "1D": [
        { time: "09:30", price: 990 },
        { time: "16:00", price: 1000 },
      ],
      "10Y": [
        { time: "2016", price: 100 },
        { time: "2026", price: 1000 },
      ],
    },
  };

  it("1D uses the broker's previous-close basis, not the intraday open", () => {
    const { container } = render(<StockChart data={nvda} loading={false} />);
    // Shows the backend's prev-close daily (-0.50%), NOT the intraday-open figure (+1.01%)
    expect(container.textContent).toContain("-0.50%");
    expect(container.textContent).not.toContain("1.01%");
  });

  it("longer ranges use the visible range (first point → current)", () => {
    render(<StockChart data={nvda} loading={false} />);
    fireEvent.click(screen.getByRole("button", { name: "10Y" }));
    const text = document.body.textContent ?? "";
    expect(text).toContain("900.00%");
    expect(text).toContain("+$900.00");
  });
});
