"""Fetch top stories from HackerNews."""

import asyncio
import aiohttp
from typing import Any, Dict, List, Optional
from src.models.article import Article
from src.storage.markdown_storage import MarkdownStorage
from src.transformers.article_transformer import ArticleTransformer
from src.utils.rate_limiter import RateLimiter


class HackerNewsFetcher:
    """
    Fetches top stories from HackerNews API.

    API Docs: https://github.com/HackerNews/API
    """

    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    def __init__(
        self,
        transformer: Optional[ArticleTransformer] = None,
        storage: Optional[MarkdownStorage] = None,
    ):
        self.transformer = transformer or ArticleTransformer()
        self.storage = storage or MarkdownStorage()
        self.rate_limiter = RateLimiter(max_concurrent=10)

    async def fetch(self, limit: int = 30) -> List[Article]:
        """
        Fetch top stories from HackerNews.

        Args:
            limit: Number of stories to fetch (default 30)

        Returns:
            List of Article objects
        """
        print(f"📰 Fetching {limit} stories from HackerNews...")

        # Step 1: Get top story IDs
        story_ids = await self._fetch_top_story_ids()

        # Step 2: Fetch first N stories concurrently
        articles = await self._fetch_stories(story_ids[:limit])

        print(f"✅ Fetched {len(articles)} HackerNews stories")
        return articles

    async def _fetch_top_story_ids(self) -> List[int]:
        """Fetch list of top story IDs."""
        url = f"{self.BASE_URL}/topstories.json"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                story_ids = await response.json()
                return story_ids

    async def _fetch_stories(self, story_ids: List[int]) -> List[Article]:
        """
        Fetch multiple stories concurrently.

        This is where async shines - fetch all at once!
        """
        # Create tasks for all stories
        tasks = [self._fetch_story(story_id) for story_id in story_ids]

        # Run all tasks concurrently
        raw_items = await asyncio.gather(*tasks)

        # Drop failed fetches and let the transformer build the Articles
        # (it also skips items without URL, e.g. Ask HN)
        return self.transformer.transform_hackernews(
            [item for item in raw_items if item is not None]
        )

    async def _fetch_story(self, story_id: int) -> Optional[Dict[str, Any]]:
        """Fetch raw story JSON by ID with rate limiting."""
        url = f"{self.BASE_URL}/item/{story_id}.json"

        try:
            async with self.rate_limiter:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        return await response.json()
        except Exception as e:
            print(f"⚠️  Failed to fetch story {story_id}: {e}")
            return None

    async def fetch_and_save(self, limit: int = 30) -> List[Article]:
        """Fetch articles and save to markdown."""
        articles = await self.fetch(limit)

        if articles:
            self.storage.save(articles, "hackernews_articles.md")

        return articles


# Test it
async def test_fetch():
    """Quick test of fetcher."""
    fetcher = HackerNewsFetcher()
    articles = await fetcher.fetch(limit=5)

    print("\n📊 Results:")
    for article in articles:
        print(f"  - {article.title[:50]}...")

    return articles


if __name__ == "__main__":
    asyncio.run(test_fetch())
