"""Orchestrate multiple news fetchers."""

import asyncio
from typing import List
from src.models.article import Article
from src.fetchers.hackernews_fetcher import HackerNewsFetcher
from src.fetchers.rss_fetcher import RSSFetcher
from src.fetchers.github_trending_fetcher import GitHubTrendingFetcher
from src.storage.markdown_storage import MarkdownStorage
from src.transformers.article_transformer import ArticleTransformer


class FetchOrchestrator:
    """
    Orchestrates fetching from multiple sources.

    Coordinates HackerNews, RSS, and other fetchers.
    """

    def __init__(self, transformer, storage):
        """Initialize orchestrator with all fetchers."""
        self.storage = storage
        self.fetchers = [
            HackerNewsFetcher(transformer, storage),
            RSSFetcher("https://hnrss.org/frontpage", transformer, storage),
            GitHubTrendingFetcher(transformer, storage),
        ]

    async def fetch_all(self) -> List[Article]:
        """
        Fetch from all sources concurrently.

        Returns:
            Combined list of all articles
        """
        print("\n🚀 Starting fetch from all sources...")
        print(f"   Sources: {len(self.fetchers)}")

        # Fetch all concurrently
        results = await asyncio.gather(
            *(fetcher.fetch_articles() for fetcher in self.fetchers),
            return_exceptions=True,
        )

        # Combine articles
        all_articles = []
        for fetcher, result in zip(self.fetchers, results):
            name = fetcher.get_source_name()
            if isinstance(result, Exception):
                print(f"⚠️  {name} failed: {result}")
            else:
                print(f"✅ {name}: {len(result)} articles")
                all_articles.extend(result)

        # Save combined results
        if all_articles:
            self.storage.save(all_articles, "all_articles.md")

        print(
            f"\n🎉 Total: {len(all_articles)} articles from {len(self.fetchers)} sources"
        )
        return all_articles


# Test it
async def main():
    """Test orchestrator."""
    orchestrator = FetchOrchestrator(ArticleTransformer(), MarkdownStorage())
    articles = await orchestrator.fetch_all()

    print("\n📊 Sample articles:")
    for article in articles[:5]:
        print(f"  [{article.source}] {article.title[:60]}...")


if __name__ == "__main__":
    asyncio.run(main())
