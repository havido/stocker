import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
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
