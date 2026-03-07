"""
Reddit scraper using PRAW.

Searches r/all for posts mentioning a stock ticker,
collects titles, selftext, and top-level comments.
"""

import os
import praw
from dotenv import load_dotenv

load_dotenv()


def _get_reddit_client() -> praw.Reddit:
    """Create and return an authenticated Reddit client."""
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "stocker/1.0")

    if not client_id or not client_secret:
        raise EnvironmentError(
            "Missing Reddit API credentials. "
            "Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in your .env file. "
            "Create an app at https://www.reddit.com/prefs/apps"
        )

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )


def scrape_reddit(ticker: str, limit: int = 10) -> list[dict]:
    """
    Search Reddit for posts about a stock ticker.

    Args:
        ticker: Stock ticker symbol (e.g. "NVDA").
        limit: Max number of posts to fetch.

    Returns:
        List of dicts with keys:
            source, title, selftext, comments, url, score
    """
    reddit = _get_reddit_client()
    results = []

    submissions = reddit.subreddit("all").search(
        ticker, time_filter="day", limit=limit
    )

    for submission in submissions:
        # Only grab existing top-level comments — don't load "more comments"
        submission.comments.replace_more(limit=0)
        top_comments = [
            comment.body
            for comment in submission.comments.list()[:20]  # cap at 20 comments
            if hasattr(comment, "body")
        ]

        results.append(
            {
                "source": "reddit",
                "title": submission.title,
                "selftext": submission.selftext or "",
                "comments": top_comments,
                "url": f"https://reddit.com{submission.permalink}",
                "score": submission.score,
            }
        )

    return results
