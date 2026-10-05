# src/fetchers/hackernews_fetcher.py

from src.fetchers.base_fetcher import BaseFetcher
import logging
from typing import List
import aiohttp
from src.models.article import Article
from src.strategies.rate_limit_strategy import SemaphoreStrategy

logger = logging.getLogger(__name__)


class HackerNewsFetcher(BaseFetcher):
    """
    Fetch top stories from HackerNews.
    
    Inherits from BaseFetcher.
    Only implements source-specific logic.
    """

    def __init__(self, transformer, storage, rate_limiter=None):
        super().__init__(transformer, storage)
        # Use provided strategy or default
        self.rate_limiter = rate_limiter or SemaphoreStrategy(10)
    
    async def fetch_articles(self) -> List[Article]:
        """Fetch from HackerNews API. Returns [] on failure (LSP contract)."""
        url = "https://hacker-news.firebaseio.com/v0/topstories.json"

        await self.rate_limiter.acquire()

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
        
        finally:
            self.rate_limiter.release()
    
    def get_source_name(self) -> str:
        """Return source name."""
        return "hackernews"
