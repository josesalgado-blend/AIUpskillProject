# src/fetchers/rss_fetcher.py

import asyncio
import logging

from src.fetchers.base_fetcher import BaseFetcher
import feedparser
from typing import List
from src.models.article import Article

logger = logging.getLogger(__name__)


class RSSFetcher(BaseFetcher):
    """Fetch from RSS feed."""

    def __init__(self, feed_url: str, transformer, storage):
        super().__init__(transformer, storage)
        self.feed_url = feed_url

    async def fetch_articles(self) -> List[Article]:
        """Fetch from RSS feed. Returns [] on failure (LSP contract)."""
        try:
            # feedparser is sync: run it in a thread so it doesn't block the event loop
            feed = await asyncio.to_thread(feedparser.parse, self.feed_url)
            return self.transformer.transform_rss(feed.entries)
        except Exception as e:
            logger.error(f"RSS fetch failed ({self.feed_url}): {e}")
            return []

    def get_source_name(self) -> str:
        """Return source name."""
        return "rss"
