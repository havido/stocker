/** Cheap client-side ticker shape check — mirrors the backend regex so we can
 *  block obviously-malformed input before hitting the API. The backend remains
 *  the source of truth for whether a (well-formed) symbol actually exists. */
const TICKER_SHAPE = /^[A-Z]{1,5}([.-][A-Z]{1,2})?$/;

/** Normalize raw user input: strip a leading $, trim, uppercase. */
export function normalizeTicker(raw: string): string {
  return raw.replace("$", "").trim().toUpperCase();
}

export function isValidTickerShape(ticker: string): boolean {
  return TICKER_SHAPE.test(ticker);
}
