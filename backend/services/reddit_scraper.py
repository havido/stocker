"""
Reddit scraper using public JSON endpoints.

No API keys required — uses reddit.com/search.json to find posts
and fetches comments via the post's .json endpoint.
"""

import time
import requests


_HEADERS = {
    "User-Agent": "stocker/1.0 (stock sentiment scraper)"
}

_BASE_SEARCH_URL = "https://www.reddit.com/search.json"


def _get_comments(permalink: str, max_comments: int = 20) -> list[str]:
    """
    Fetch top-level comments for a post using its JSON endpoint.

    Args:
        permalink: The post's permalink (e.g. /r/stocks/comments/abc123/...).
        max_comments: Max number of comments to return.

    Returns:
        List of comment body strings.
    """
    url = f"https://www.reddit.com{permalink}.json"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return []

    comments = []
    # Reddit returns [post_listing, comments_listing]
    if isinstance(data, list) and len(data) > 1:
        comment_listing = data[1].get("data", {}).get("children", [])
        for child in comment_listing[:max_comments]:
            if child.get("kind") == "t1":  # t1 = comment
                body = child.get("data", {}).get("body", "")
                if body:
                    comments.append(body)

    return comments


def scrape_reddit(ticker: str, limit: int = 10, log_callback=None) -> list[dict]:
    """
    Search Reddit for posts about a stock ticker using public JSON endpoints.

    Args:
        ticker: Stock ticker symbol (e.g. "NVDA").
        limit: Max number of posts to fetch.

    Returns:
        List of dicts with keys:
            source, title, selftext, comments, url, score
    """
    params = {
        "q": ticker,
        "sort": "relevance",
        "t": "day",
        "limit": limit,
        "type": "link",
    }

    try:
        resp = requests.get(_BASE_SEARCH_URL, headers=_HEADERS, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        print(f"        Reddit search request failed: {e}")
        return []

    posts = data.get("data", {}).get("children", [])
    results = []
    scraped_count = 0

    for post in posts:
        post_data = post.get("data", {})
        permalink = post_data.get("permalink", "")

        # Rate limit: Reddit public endpoints throttle aggressively
        time.sleep(1)

        comments = _get_comments(permalink)
        
        scraped_count += 1 + len(comments)
        
        if log_callback:
            log_callback(f'{{"step": "reddit", "message": "Scraping {scraped_count} Reddit articles for ${ticker}..."}}')

        results.append(
            {
                "source": "reddit",
                "title": post_data.get("title", ""),
                "selftext": post_data.get("selftext", ""),
                "comments": comments,
                "url": f"https://reddit.com{permalink}",
                "score": post_data.get("score", 0),
            }
        )

    return results
