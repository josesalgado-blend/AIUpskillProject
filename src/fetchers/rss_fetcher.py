# src/fetchers/rss_fetcher.py

import asyncio

from src.fetchers.base_fetcher import BaseFetcher
import feedparser
from typing import List
from src.models.article import Article


class RSSFetcher(BaseFetcher):
    """Fetch from RSS feed."""
    
    def __init__(self, feed_url: str, transformer, storage):
        super().__init__(transformer, storage)
        self.feed_url = feed_url
    
    async def fetch_articles(self) -> List[Article]:
        """Fetch from RSS feed."""
        # feedparser is sync: run it in a thread so it doesn't block the event loop
        feed = await asyncio.to_thread(feedparser.parse, self.feed_url)
        return self.transformer.transform_rss(feed.entries)
    
    def get_source_name(self) -> str:
        """Return source name."""
        return "rss"
