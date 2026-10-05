# src/fetchers/hackernews_fetcher.py

from src.fetchers.base_fetcher import BaseFetcher
import logging
from typing import List
import aiohttp
from src.models.article import Article

logger = logging.getLogger(__name__)


class HackerNewsFetcher(BaseFetcher):
    """
    Fetch top stories from HackerNews.
    
    Inherits from BaseFetcher.
    Only implements source-specific logic.
    """
    
    async def fetch_articles(self) -> List[Article]:
        """Fetch from HackerNews API. Returns [] on failure (LSP contract)."""
        url = "https://hacker-news.firebaseio.com/v0/topstories.json"

        try:
            async with aiohttp.ClientSession() as session:
                # Get top story IDs
                async with session.get(url) as response:
                    story_ids = await response.json()

                # Fetch first 30 stories
                stories = []
                for story_id in story_ids[:30]:
                    item_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                    async with session.get(item_url) as response:
                        item = await response.json()
                        if item:
                            stories.append(item)

                # Transform using injected transformer
                return self.transformer.transform_hackernews(stories)
        except Exception as e:
            logger.error(f"HackerNews fetch failed: {e}")
            return []
    
    def get_source_name(self) -> str:
        """Return source name."""
        return "hackernews"
