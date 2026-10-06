# Architecture

How the system is built **as it stands today**. For the curriculum-level
orientation (what you are going to build, week by week) read
[`architecture/overview.md`](architecture/overview.md); for the reasoning behind
the refactoring see [`design-decisions.md`](design-decisions.md).

## System overview

A multi-agent pipeline that fetches tech news, keeps what is relevant to AI/ML,
summarizes it by topic and writes a daily newsletter. It runs locally.

```
HackerNews | GitHub Trending | RSS
        │  async fetchers (BaseFetcher)
        ▼
FetchOrchestrator ──► data/articles/*.md
        │
        ├──► SQLite (data/news_agent.db) ◄── Database MCP server ◄── SearchSkill
        ▼
NewsFilterAgent  ──► data/context/filtered_articles.md
        ▼
SummarizerAgent  ──► data/context/summary.md
        ▼
WriterAgent      ──► data/output/newsletter.md
```

The agents exchange data through markdown files. The database is filled by the
pipeline and can be queried through the MCP server, but no agent reads from it
yet (`SummarizerAgent` creates a `SearchSkill` it does not use).

## Design principles

**SOLID**
- *Single responsibility*: fetchers fetch, `ArticleTransformer` converts raw data
  into `Article`, `MarkdownStorage` saves files.
- *Open/Closed*: a new source is a new class that inherits `BaseFetcher`;
  `GitHubTrendingFetcher` was added without editing any existing fetcher.
- *Liskov*: every fetcher returns a `List[Article]` and returns `[]` on errors
  instead of raising, so fetchers are interchangeable (`tests/test_substitutability.py`).
- *Interface segregation*: `BaseFetcher` only has what all fetchers need;
  `AuthenticatedFetcher` and `PaginatedFetcher` are optional interfaces.
- *Dependency inversion*: `FetchOrchestrator` and the fetchers receive their
  transformer and storage through the constructor and depend on `ArticleStorage`.

**Patterns actually used**
- *Template Method*: `BaseFetcher.fetch_and_save()` and `BaseAgent.execute()`
  (load → process → save); subclasses fill in the steps.
- *Factory*: `FetcherFactory` creates fetchers by name and can be extended with
  `register()`.
- *Strategy*: `RateLimitStrategy` with `SemaphoreStrategy` (used by
  `HackerNewsFetcher`) and `TokenBucketStrategy`.

## Components

### Fetchers (`src/fetchers/`)

| Fetcher | Source | Notes |
|---|---|---|
| `HackerNewsFetcher` | HackerNews API | Top 30 stories, semaphore rate limiting |
| `GitHubTrendingFetcher` | github.com/trending | Scrapes up to 20 repositories (BeautifulSoup) |
| `RSSFetcher` | any RSS feed | `feedparser` runs in a thread (`asyncio.to_thread`) |

Fetchers catch their own errors, log them and return an empty list. The
orchestrator calls them one after another and saves one file per source
(`<source>_articles.md`).

### Agents (`src/agents/`)

- **`BaseAgent`**: template method, LiteLLM call helper, tool-call loop (capped at
  10 rounds), retries (`LLM_NUM_RETRIES`) and a minimum interval between calls
  (`LLM_MIN_INTERVAL`).
- **`NewsFilterAgent`**: asks the LLM for `relevant`, `relevance_score` (1-10),
  `reasoning` and `key_topics` as JSON; keeps articles with a score of at least 6.
  Articles it cannot judge (quota, network, invalid JSON) are counted and reported
  as an INCOMPLETE result; they are never treated as "not relevant".
- **`EnhancedFilterAgent`**: same filter with tool access (`calculator`, mocked
  `web_search`).
- **`SummarizerAgent`**: groups the kept articles by their first key topic and
  asks the LLM for a short summary per topic.
- **`WriterAgent`**: turns the summary into the newsletter.

### MCP (`src/mcp/`, `src/database/`, `src/skills/`)

- **Database server** (`src/mcp/database_server.py`): stdio MCP server with three
  tools, `query_articles`, `search_articles` and `get_sources`, on top of SQLite
  (`articles` table, unique `url`, parameterized queries).
- **`SearchSkill`**: a client that starts the server and wraps `search_articles`.
- **Conventions that matter**: stdout is the protocol channel, so servers log to
  stderr; clients start servers with `sys.executable`, `-X utf8` and `-m
  src.mcp.<server>` so they use the same interpreter, encoding and import path.

### Evaluation (`src/evaluation/`)

`FilterEvaluator` runs `NewsFilterAgent` over `data/evaluation/golden_dataset.json`
(10 labeled cases) and reports accuracy, precision, recall and F1. Cases the agent
cannot judge are excluded and flagged; if none can be judged it raises.

## Data flow

1. External APIs → fetchers (async).
2. `Article` objects → markdown files in `data/articles/` and rows in SQLite.
3. `all_articles.md` → `NewsFilterAgent` → `filtered_articles.md`.
4. `filtered_articles.md` → `SummarizerAgent` → `summary.md`.
5. `summary.md` → `WriterAgent` → `data/output/newsletter.md`.

Markdown keeps every stage human-readable and diff-able, at the price of a little
parsing code.

## Technology choices

- **Python 3.11 with async/await**: I/O is async (`aiohttp`, threads for sync libraries).
- **LiteLLM**: the model is chosen with `LITELLM_MODEL`, with no code changes. The
  project was run with Gemini and with Groq (`groq/openai/gpt-oss-120b`).
- **SQLite**: no server, enough for a local pipeline.
- **MCP**: tools exposed over a standard protocol, reusable by any client.
- **Markdown**: readable, git-friendly and a natural LLM format.

## Performance (measured)

| Stage | Time |
|---|---|
| Fetch ~44 articles (`python -m src.main`) | ~6 s |
| Complete pipeline, 44 articles, Groq free tier, `LLM_MIN_INTERVAL=7` | ~6 min (342-356 s) |
| `EnhancedFilterAgent` over 43 articles | ~9 min |
| Evaluation (10 cases) | ~1-2 min with the same pacing |

The pipeline time is dominated by waiting between LLM calls, not by the model: on
the Groq free tier the limit is about 8,000 tokens per minute. The orchestrator
runs fetchers sequentially, so the fetch step is not concurrent.

## Error handling

- Fetchers return `[]` on failure.
- LLM calls retry (`num_retries`, needs `tenacity`) and are paced.
- Agents mark failed judgments as errors and report how many articles were affected.
- The evaluator excludes errored cases and fails if all of them errored.
- LLM-backed tests fall back to mock responses when the provider fails.

## Security

- API keys live in `.env`, which is git-ignored; they are read at runtime and not
  logged.
- SQL uses parameterized queries.
- LLM output is parsed with `json.loads` and validated.
- **Known risk:** the `calculator` tool runs `eval()` with empty builtins on
  text the model produces. It is not a sandbox; do not expose it to untrusted input.

## Testing

`pytest tests/`: 41 passing, 3 skipped (manual scripts run with `python -m`), 64 %
line coverage. See the [README](../README.md#running-tests).

## Future enhancements

1. Make agents use the database (for example `SummarizerAgent` through `SearchSkill`).
2. Run fetchers concurrently with `asyncio.gather`.
3. A larger golden dataset with harder cases.
4. More sources (arXiv, Reddit) through new `BaseFetcher` subclasses.
5. Scheduled runs and a container image (see [`deployment.md`](deployment.md)).
