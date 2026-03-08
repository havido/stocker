// Mock data for the stock sentiment dashboard

export interface StockData {
  ticker: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
}

export interface PricePoint {
  time: string;
  price: number;
}

export interface SentimentSource {
  name: string;
  platform: "twitter" | "reddit" | "yahoo";
  sentiment: "positive" | "negative" | "neutral";
  score: number;
  snippet: string;
  time: string;
}

export interface CorrelationEntry {
  factor: string;
  rScore: number;
  reasoning: string;
}

export const MOCK_STOCK: StockData = {
  ticker: "AAPL",
  name: "Apple Inc.",
  price: 198.11,
  change: 3.47,
  changePercent: 1.78,
};

const generatePriceData = (points: number, base: number, volatility: number): PricePoint[] => {
  const data: PricePoint[] = [];
  let price = base;
  const now = Date.now();
  for (let i = 0; i < points; i++) {
    price += (Math.random() - 0.47) * volatility;
    price = Math.max(price * 0.95, price);
    data.push({
      time: new Date(now - (points - i) * 60000 * (points > 100 ? 60 : 1)).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      price: Math.round(price * 100) / 100,
    });
  }
  return data;
};

export const MOCK_PRICES: Record<string, PricePoint[]> = {
  "1D": generatePriceData(78, 194, 0.6),
  "1W": generatePriceData(35, 190, 1.5),
  "1M": generatePriceData(30, 185, 3),
  "1Y": generatePriceData(52, 160, 5),
  ALL: generatePriceData(100, 120, 6),
};

export const MOCK_SENTIMENT_SCORE = 0.72;

export const MOCK_SOURCES: SentimentSource[] = [
  { name: "@MarketWatch", platform: "twitter", sentiment: "positive", score: 0.85, snippet: "Apple's new AI features could drive significant upgrade cycle in 2026. $AAPL", time: "12m ago" },
  { name: "r/wallstreetbets", platform: "reddit", sentiment: "positive", score: 0.62, snippet: "AAPL earnings beat expectations — calls printing 🚀", time: "34m ago" },
  { name: "Yahoo Finance", platform: "yahoo", sentiment: "neutral", score: 0.1, snippet: "Apple maintains steady growth amid global supply chain uncertainty.", time: "1h ago" },
  { name: "@InvestorDaily", platform: "twitter", sentiment: "negative", score: -0.3, snippet: "Concerned about AAPL valuation at these levels. P/E getting stretched.", time: "2h ago" },
  { name: "r/stocks", platform: "reddit", sentiment: "positive", score: 0.71, snippet: "Long AAPL — services revenue is the real story here.", time: "3h ago" },
];

export const MOCK_CORRELATIONS: CorrelationEntry[] = [
  { factor: "Social Media Volume", rScore: 0.87, reasoning: "High positive tweet volume preceded 3-day price rally in 78% of cases." },
  { factor: "Reddit Sentiment", rScore: 0.72, reasoning: "WSB bullish consensus aligns with short-term upward momentum." },
  { factor: "News Sentiment (finBERT)", rScore: 0.65, reasoning: "finBERT classifies recent earnings coverage as predominantly positive (confidence: 0.91)." },
  { factor: "Analyst Consensus", rScore: 0.58, reasoning: "12 of 15 analysts maintain Buy rating with average PT of $215." },
];

export const MOCK_WATCHLIST = [
  { ticker: "AAPL", name: "Apple Inc.", price: 198.11, change: 1.78 },
  { ticker: "TSLA", name: "Tesla Inc.", price: 241.37, change: -2.14 },
  { ticker: "NVDA", name: "NVIDIA Corp.", price: 875.28, change: 4.23 },
  { ticker: "MSFT", name: "Microsoft", price: 425.52, change: 0.91 },
  { ticker: "GOOGL", name: "Alphabet Inc.", price: 171.83, change: -0.45 },
];
