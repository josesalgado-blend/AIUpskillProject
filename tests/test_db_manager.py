# tests/test_db_manager.py
"""DatabaseManager tests on a temporary SQLite file (no network)."""

import pytest
import pytest_asyncio

from src.database.db_manager import DatabaseManager


def _article(n: int, source: str = "test", published: str = "2026-01-01T00:00:00"):
    return {
        "title": f"Article {n}",
        "url": f"https://example.com/{n}",
        "source": source,
        "published_at": published,
        "summary": f"Summary {n}",
    }


@pytest_asyncio.fixture
async def db(tmp_path):
    manager = DatabaseManager(str(tmp_path / "nested" / "news.db"))
    await manager.initialize()
    return manager


@pytest.mark.asyncio
async def test_initialize_creates_parent_dir_and_is_idempotent(tmp_path):
    path = tmp_path / "nested" / "news.db"
    manager = DatabaseManager(str(path))

    await manager.initialize()
    await manager.initialize()  # CREATE TABLE IF NOT EXISTS: must not fail

    assert path.exists()
    assert await manager.query_articles() == []


@pytest.mark.asyncio
async def test_insert_and_query_roundtrip(db):
    await db.insert_article(_article(1))

    rows = await db.query_articles()

    assert len(rows) == 1
    assert rows[0]["title"] == "Article 1"
    assert rows[0]["score"] == 0  # default


@pytest.mark.asyncio
async def test_duplicate_url_is_ignored(db):
    await db.insert_article(_article(1))
    await db.insert_article(_article(1))  # same URL

    assert len(await db.query_articles()) == 1


@pytest.mark.asyncio
async def test_query_filters_by_source_and_limit_newest_first(db):
    await db.insert_article(_article(1, "hackernews", "2026-01-01T00:00:00"))
    await db.insert_article(_article(2, "hackernews", "2026-01-03T00:00:00"))
    await db.insert_article(_article(3, "rss", "2026-01-02T00:00:00"))

    only_hn = await db.query_articles(source="hackernews")
    assert [r["title"] for r in only_hn] == ["Article 2", "Article 1"]

    assert len(await db.query_articles(limit=2)) == 2
