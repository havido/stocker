"""
Yahoo Finance scraper.

Uses yfinance to find news article URLs for a ticker,
then requests + BeautifulSoup to extract article body text.
"""

import requests
from bs4 import BeautifulSoup
import yfinance as yf


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _extract_article_text(url: str, timeout: int = 10) -> str:
    """
    Fetch a URL and extract the main article text.

    Returns the concatenated paragraph text, or an empty string on failure.
    """
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()
    except (requests.RequestException, Exception):
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove script/style tags
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    # Try common article containers first
    article = soup.find("article") or soup.find("div", class_="caas-body")
    container = article if article else soup

    paragraphs = container.find_all("p")
    text = " ".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    return text


def scrape_yahoo(ticker: str, log_callback=None) -> list[dict]:
    """
    Get news articles for a stock ticker from Yahoo Finance.

    Args:
        ticker: Stock ticker symbol (e.g. "NVDA").

    Returns:
        List of dicts with keys:
            source, title, url, body
    """
    results = []
    scraped_count = 0

    try:
        search = yf.Search(ticker, news_count=10)
        news_items = search.news or []
    except Exception:
        news_items = []

    for item in news_items:
        title = item.get("title", "")
        url = item.get("link", "")

        if not url:
            continue

        body = _extract_article_text(url)
        
        if body:
            scraped_count += 1
            if log_callback:
                log_callback(f'{{"step": "yahoo", "message": "Scraping {scraped_count} Yahoo Finance articles for ${ticker}..."}}')

        results.append(
            {
                "source": "yahoo",
                "title": title,
                "url": url,
                "body": body,
            }
        )

    return results
