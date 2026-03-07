"""
Stock Sentiment Scraper — Main entry point.

Usage:
    python main.py NVDA          # analyze a single ticker
    python main.py               # analyze all default tickers
    python main.py NVDA TSLA     # analyze multiple tickers
"""

import json
import sys
from datetime import datetime, timezone

from reddit_scraper import scrape_reddit
from yahoo_scraper import scrape_yahoo
from sentiment import analyze_sentiment, compute_summary


DEFAULT_TICKERS = ["NVDA", "TSLA", "AAPL", "GME", "PLTR", "META", "MSFT", "GOOGL", "AMZN"]


def analyze_ticker(ticker: str) -> dict:
    """
    Run the full scrape → sentiment pipeline for a single ticker.

    Returns a dict ready for JSON serialization.
    """
    ticker = ticker.upper()
    print(f"\n{'='*60}")
    print(f"  Analyzing: {ticker}")
    print(f"{'='*60}")

    # --- Reddit ---
    print(f"  [1/3] Scraping Reddit for '{ticker}'...")
    try:
        reddit_posts = scrape_reddit(ticker)
        print(f"        Found {len(reddit_posts)} Reddit posts")
    except Exception as e:
        print(f"        Reddit scrape failed: {e}")
        reddit_posts = []

    # --- Yahoo Finance ---
    print(f"  [2/3] Scraping Yahoo Finance for '{ticker}'...")
    try:
        yahoo_articles = scrape_yahoo(ticker)
        print(f"        Found {len(yahoo_articles)} Yahoo articles")
    except Exception as e:
        print(f"        Yahoo scrape failed: {e}")
        yahoo_articles = []

    # --- Collect texts for sentiment analysis ---
    reddit_texts = []
    for post in reddit_posts:
        # Combine title + selftext as one entry
        combined = f"{post['title']}. {post['selftext']}".strip()
        if combined:
            reddit_texts.append(combined)
        # Each comment as a separate entry
        reddit_texts.extend([c for c in post["comments"] if c.strip()])

    yahoo_texts = []
    for article in yahoo_articles:
        # Use title + body
        combined = f"{article['title']}. {article['body']}".strip()
        if combined:
            yahoo_texts.append(combined)

    # --- Sentiment analysis ---
    print(f"  [3/3] Running FinBERT sentiment analysis...")
    reddit_sentiments = analyze_sentiment(reddit_texts)
    yahoo_sentiments = analyze_sentiment(yahoo_texts)
    all_sentiments = reddit_sentiments + yahoo_sentiments

    # --- Build output ---
    # Tag reddit sentiments back to their posts
    reddit_output = []
    idx = 0
    for post in reddit_posts:
        if idx < len(reddit_sentiments):
            post_sentiment = reddit_sentiments[idx]
            idx += 1
        else:
            post_sentiment = {"label": "neutral", "score": 0.0}
        # Skip past comment sentiments
        idx += len(post["comments"])
        reddit_output.append(
            {
                "title": post["title"],
                "url": post["url"],
                "score": post["score"],
                "sentiment": {
                    "label": post_sentiment["label"],
                    "score": post_sentiment["score"],
                },
            }
        )

    yahoo_output = []
    for i, article in enumerate(yahoo_articles):
        if i < len(yahoo_sentiments):
            art_sentiment = yahoo_sentiments[i]
        else:
            art_sentiment = {"label": "neutral", "score": 0.0}
        yahoo_output.append(
            {
                "title": article["title"],
                "url": article["url"],
                "sentiment": {
                    "label": art_sentiment["label"],
                    "score": art_sentiment["score"],
                },
            }
        )

    overall = compute_summary(all_sentiments)

    result = {
        "ticker": ticker,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reddit": {
            "posts_scraped": len(reddit_posts),
            "sentiments": reddit_output,
        },
        "yahoo": {
            "articles_scraped": len(yahoo_articles),
            "sentiments": yahoo_output,
        },
        "overall": overall,
    }

    print(f"  ✓ Verdict: {overall['verdict'].upper()}")
    return result


def main():
    """Entry point — parse CLI args and run analysis."""
    if len(sys.argv) > 1:
        tickers = [t.upper() for t in sys.argv[1:]]
    else:
        tickers = DEFAULT_TICKERS

    results = []
    for ticker in tickers:
        result = analyze_ticker(ticker)
        results.append(result)

    # If single ticker, output just the dict; otherwise output a list
    output = results[0] if len(results) == 1 else results

    print(f"\n{'='*60}")
    print("  JSON Output")
    print(f"{'='*60}")
    print(json.dumps(output, indent=2))

    return output


if __name__ == "__main__":
    main()
