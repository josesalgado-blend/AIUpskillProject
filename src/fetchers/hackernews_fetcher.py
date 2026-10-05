# src/fetchers/hackernews_fetcher.py

from src.fetchers.base_fetcher import BaseFetcher
from typing import List
import aiohttp
from src.models.article import Article


class HackerNewsFetcher(BaseFetcher):
    """
    Fetch top stories from HackerNews.
    
    Inherits from BaseFetcher.
    Only implements source-specific logic.
    """
    
    async def fetch_articles(self) -> List[Article]:
        """Fetch from HackerNews API."""
        url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        
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
    
    def get_source_name(self) -> str:
        """Return source name."""
        return "hackernews"
