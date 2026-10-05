"""Fetch from GitHub Trending."""
from src.fetchers.base_fetcher import BaseFetcher
import logging
from typing import List
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
from src.models.article import Article

logger = logging.getLogger(__name__)


class GitHubTrendingFetcher(BaseFetcher):
    """
    Fetch trending repositories from GitHub.
    
    NEW fetcher - demonstrates Open/Closed Principle.
    Added WITHOUT modifying any existing code!
    """
    
    async def fetch_articles(self) -> List[Article]:
        """Scrape GitHub trending page. Returns [] on failure (LSP contract)."""
        url = "https://github.com/trending"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    html = await response.text()

            soup = BeautifulSoup(html, 'html.parser')
            repos = soup.select('article.Box-row')

            articles = []
            for repo in repos[:20]:  # Top 20
                # Extract repo info
                title_elem = repo.select_one('h2 a')
                if not title_elem:
                    continue

                title = title_elem.text.strip().replace('\n', '').replace(' ', '')
                href = title_elem['href']
                url = f"https://github.com{href}"

                description_elem = repo.select_one('p')
                description = description_elem.text.strip() if description_elem else ''

                stars_elem = repo.select_one('span.d-inline-block.float-sm-right')
                stars = stars_elem.text.strip() if stars_elem else '0'

                article = Article(
                    title=title,
                    url=url,
                    published_at=datetime.now(),
                    source='github_trending',
                    summary=f"{description} (⭐ {stars})",
                    score=0
                )
                articles.append(article)

            return articles
        except Exception as e:
            logger.error(f"GitHub Trending fetch failed: {e}")
            return []
    
    def get_source_name(self) -> str:
        """Return source name."""
        return "github_trending"


# Quick test
from src.fetchers.github_trending_fetcher import GitHubTrendingFetcher
from src.transformers.article_transformer import ArticleTransformer
from src.storage.markdown_storage import MarkdownStorage

async def test_github():
    transformer = ArticleTransformer()
    storage = MarkdownStorage()
    
    fetcher = GitHubTrendingFetcher(transformer, storage)
    articles = await fetcher.fetch_and_save()
    
    print(f"✅ Fetched {len(articles)} trending repos!")
    print(f"First: {articles[0].title}")

# Run it
import asyncio
asyncio.run(test_github())

