import { describe, it, expect } from "vitest";
import { normalizeTicker, isValidTickerShape } from "@/lib/ticker";

describe("normalizeTicker", () => {
  it("strips $, trims, and uppercases", () => {
    expect(normalizeTicker("  $aapl ")).toBe("AAPL");
  });
});

describe("isValidTickerShape", () => {
  it.each(["A", "AAPL", "GOOGL", "BRK.B", "BRK-B"])("accepts %s", (s) => {
    expect(isValidTickerShape(s)).toBe(true);
  });

  it.each(["", "ASDFGH", "AA PL", "AA!", "123"])("rejects %s", (s) => {
    expect(isValidTickerShape(s)).toBe(false);
  });
});
