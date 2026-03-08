import asyncio
from services.reddit_scraper import scrape_reddit
from services.yahoo_scraper import scrape_yahoo

class StockScraper:
    async def fetch_data(self, ticker: str) -> list[str]:
        # Scrape Reddit and Yahoo directly
        reddit_posts = scrape_reddit(ticker)
        yahoo_articles = scrape_yahoo(ticker)
        
        # Collect texts
        texts = []
        for post in reddit_posts:
            combined = f"{post.get('title', '')}. {post.get('selftext', '')}".strip()
            if combined:
                texts.append(combined)
            texts.extend([c for c in post.get("comments", []) if c.strip()])
            
        for article in yahoo_articles:
            combined = f"{article.get('title', '')}. {article.get('body', '')}".strip()
            if combined:
                texts.append(combined)
                
        return [t for t in texts if t]
