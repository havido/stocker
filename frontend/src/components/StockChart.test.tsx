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
  // current price 1000; intraday started at 1005 (-0.50%); 10Y started at 100 (+900%)
  const nvda: StockChartData = {
    ticker: "NVDA",
    name: "NVIDIA",
    price: 1000,
    change: -5, // backend's 1-day figure — must NOT be shown for 10Y
    changePercent: -0.5,
    history: {
      "1D": [
        { time: "09:30", price: 1005 },
        { time: "16:00", price: 1000 },
      ],
      "10Y": [
        { time: "2016", price: 100 },
        { time: "2026", price: 1000 },
      ],
    },
  };

  it("reflects the selected period, not just the day", () => {
    const { container } = render(<StockChart data={nvda} loading={false} />);

    // 1D (default): intraday change ≈ -0.50%, NOT the 10-year number
    expect(container.textContent).toContain("0.50%");
    expect(container.textContent).not.toContain("900.00%");

    // Switch to 10Y → gain/loss recomputes over the whole range (+900%)
    fireEvent.click(screen.getByRole("button", { name: "10Y" }));
    expect(container.textContent).toContain("900.00%");
    expect(container.textContent).toContain("+$900.00");
  });
});
