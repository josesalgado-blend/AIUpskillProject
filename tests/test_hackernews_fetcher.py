"""Tests for HackerNews fetcher."""

import pytest
from src.fetchers.hackernews_fetcher import HackerNewsFetcher
from src.models.article import Article
from src.transformers.article_transformer import ArticleTransformer
from src.storage.markdown_storage import MarkdownStorage


@pytest.mark.asyncio
async def test_fetch_returns_articles(tmp_path):
    """Test that fetch_articles returns list of articles."""
    fetcher = HackerNewsFetcher(ArticleTransformer(), MarkdownStorage(str(tmp_path)))
    articles = await fetcher.fetch_articles()

    # Should get some articles (the fetcher reads the top 30 stories)
    assert len(articles) > 0
    assert len(articles) <= 30

    # Each should be an Article
    for article in articles:
        assert isinstance(article, Article)
        assert article.title
        assert article.url
        assert article.source == "hackernews"


@pytest.mark.asyncio
async def test_hackernews_fetcher():
    """Test HackerNews fetcher with new architecture."""
    transformer = ArticleTransformer()
    storage = MarkdownStorage("data/test_articles")

    fetcher = HackerNewsFetcher(transformer=transformer, storage=storage)

    articles = await fetcher.fetch_articles()

    assert len(articles) > 0
    assert all(hasattr(a, "title") for a in articles)
