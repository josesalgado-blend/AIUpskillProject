# AI Upskill Project

**Multi-agent news pipeline with MCP integration**

An AI agent pipeline that fetches tech news, keeps what is relevant to AI/ML,
summarizes it by topic and writes a daily newsletter. It was built milestone by
milestone as part of Blend's AI engineering onboarding curriculum.

## Features

- 🚀 **Async news fetching** from HackerNews and GitHub Trending (an RSS fetcher is also included), with rate limiting
- 🤖 **AI-powered filtering** through LiteLLM. Provider-agnostic: change one env var to swap models (run with Gemini and with Groq `gpt-oss-120b`)
- 🔧 **MCP integration**: a database MCP server with 3 tools and a reusable `SearchSkill` client
- 📝 **Three-agent pipeline**: Filter → Summarize → Write
- 💾 **SQLite database** for article storage
- 📊 **Evaluation framework**: golden dataset with accuracy, precision, recall and F1
- ✅ **Tests** with pytest. LLM-backed tests try the real model first and fall back to mocks if the provider is unavailable (quota, outage, no key)

## Quick start

### Prerequisites

- Python 3.11+
- One LLM provider API key. Any [LiteLLM-supported provider](https://docs.litellm.ai/docs/providers) works; free options include Groq and Gemini

### Installation

```bash
git clone https://github.com/josesalgado-blend/AIUpskillProject.git
cd AIUpskillProject

python -m venv venv
source venv/bin/activate          # macOS/Linux
# venv\Scripts\activate           # Windows

pip install -r requirements.txt

cp .env.example .env              # then edit .env (see Configuration)
python scripts/verify_setup.py
```

### Configuration

Set these in `.env` (it is git-ignored, never commit keys):

| Variable | Required | Description |
|---|---|---|
| `LITELLM_MODEL` | yes | Model string, e.g. `groq/openai/gpt-oss-120b`, `gemini/<model>` or `claude-haiku-4-5-20251001` |
| `<PROVIDER>_API_KEY` | yes | The key matching the model's provider: `GROQ_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`... |
| `LLM_MIN_INTERVAL` | no | Seconds to wait between LLM calls (default `0`). Use it on free tiers with tokens-per-minute limits, e.g. `7` for Groq |
| `LLM_NUM_RETRIES` | no | Retries on transient LLM errors (default `2`) |

### Run the complete pipeline

```bash
python -X utf8 -m src.complete_pipeline
```

It fetches articles, stores them in SQLite, filters them with the LLM, summarizes
them by topic and writes the newsletter:

- `data/output/newsletter.md`: final newsletter
- `data/context/`: intermediate outputs (`filtered_articles.md`, `summary.md`)
- `data/articles/`: fetched articles (markdown)
- `data/news_agent.db`: article database

With a free tier that needs pacing (`LLM_MIN_INTERVAL=7`) a run over about 43
articles takes roughly 6 minutes, because most of the time is spent waiting
between LLM calls.

> **Windows:** run Python with `-X utf8` (or set `PYTHONUTF8=1`). The programs
> print emoji and read UTF-8 markdown, which the default Windows console
> encoding cannot handle. Always run modules from the project root with `-m`
> so that `src` is importable.

### Run individual components

```bash
python -X utf8 -m src.main                  # fetch articles only
python -X utf8 -m src.pipeline              # fetch + filter
python -X utf8 -m src.evaluation.evaluator  # evaluate the filter agent
python -X utf8 -m tests.test_enhanced_agent # filter agent with tool use (calculator, mock web_search)

python -X utf8 -m src.database.populate_db  # load data/articles/*.md into SQLite
python -X utf8 -m src.mcp.simple_client     # MCP hello world server + client
python -X utf8 -m tests.test_db_server      # try the database MCP server
python -X utf8 -m src.skills.search_skill   # SearchSkill over the database server
```

## Architecture

```
┌──────────────────────────────────────────┐
│  News sources                            │
│  HackerNews | GitHub Trending | RSS      │
└────────────────────┬─────────────────────┘
                     │ async fetchers
                     ▼
          ┌─────────────────────┐
          │  FetchOrchestrator  │──► data/articles/*.md
          └──────────┬──────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
   ┌───────────┐         ┌───────────────┐
   │  SQLite   │◄────────│ Database MCP  │  (query / search / get_sources,
   │ articles  │         │    server     │   used through SearchSkill)
   └───────────┘         └───────────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │   NewsFilterAgent   │  LLM relevance score per article
          └──────────┬──────────┘
                     ▼
          ┌─────────────────────┐
          │   SummarizerAgent   │  groups by topic, summarizes
          └──────────┬──────────┘
                     ▼
          ┌─────────────────────┐
          │    WriterAgent      │  writes the newsletter
          └──────────┬──────────┘
                     ▼
              📄 newsletter.md
```

The database is filled by the pipeline and can be queried through the MCP
server; the three agents exchange data through markdown files in `data/`.

See [`docs/architecture/overview.md`](docs/architecture/overview.md) and
[`docs/design-decisions.md`](docs/design-decisions.md) for the design reasoning.

## Project structure

```
AIUpskillProject/
├── src/
│   ├── agents/          # BaseAgent, NewsFilterAgent, EnhancedFilterAgent, SummarizerAgent, WriterAgent
│   ├── fetchers/        # BaseFetcher, HackerNews, RSS, GitHub Trending
│   ├── factories/       # FetcherFactory
│   ├── strategies/      # rate limiting strategies
│   ├── transformers/    # raw data -> Article
│   ├── storage/         # ArticleStorage interface, MarkdownStorage
│   ├── orchestration/   # FetchOrchestrator
│   ├── database/        # SQLite manager and populate script
│   ├── mcp/             # MCP servers and client (hello world, database)
│   ├── skills/          # SearchSkill
│   ├── tools/           # LLM-callable tools (calculator, web_search)
│   ├── evaluation/      # FilterEvaluator
│   ├── models/          # Article
│   ├── main.py          # fetch only
│   ├── pipeline.py      # fetch + filter
│   └── complete_pipeline.py
├── tests/
├── scripts/             # verify_setup.py, examples
├── data/
│   ├── articles/        # fetched articles
│   ├── context/         # agent outputs
│   ├── output/          # final newsletter
│   └── evaluation/      # golden dataset and report
└── docs/
```

## Key technologies

- **Python 3.11+**: async/await throughout
- **aiohttp** and **feedparser**: HTTP and RSS
- **LiteLLM**: LLM provider abstraction
- **MCP** (`mcp`): Model Context Protocol servers and clients
- **SQLite** (`aiosqlite`): local article database
- **pytest**, **pytest-asyncio**, **pytest-cov**: testing
- **ruff**: formatting and linting

## Evaluation

The filter agent is evaluated against a hand-labeled golden dataset
(`data/evaluation/golden_dataset.json`, 10 cases):

```bash
python -X utf8 -m src.evaluation.evaluator   # writes data/evaluation/evaluation_report.md
```

With `groq/openai/gpt-oss-120b` the agent got 10/10 correct
(accuracy, precision and recall 100 %, F1 1.000). Treat this with care: the
dataset is small and easy, and two of its cases are close to the examples in the
agent's prompt. It is a regression check, not a quality benchmark.

Test cases the agent cannot judge (API quota, network, invalid response) are
**excluded** from the metrics and flagged as `INCOMPLETE` in the report; if none
can be judged the evaluation fails instead of reporting 0 %.

## Running tests

```bash
pytest tests/ -v

# with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

The suite currently has 24 passing tests and 3 skipped ones (manual scripts that
you run with `python -m`). Tests that use an LLM call the real model first and
use mock responses if it fails, so the suite never depends on the provider.

## Development

### Code style

```bash
ruff format src tests
ruff check src tests
```

### Adding a news source

1. Create a fetcher in `src/fetchers/` that inherits from `BaseFetcher`.
2. Implement `fetch_articles()` and `get_source_name()`. Return an empty list on
   errors instead of raising, so any fetcher can replace another.
3. Register it with `FetcherFactory.register(name, YourFetcher)`, or add an
   instance to the `fetchers` list you pass to `FetchOrchestrator`.

No existing fetcher needs to change.

### Adding an MCP tool

1. Add a `Tool(...)` with an `inputSchema` in `list_tools()` of the server.
2. Handle it in `call_tool()`.
3. Test it with an MCP client.

Notes for MCP servers (stdio transport): stdout is the protocol channel, so log
to **stderr**, never to stdout; and launch servers as modules with the same
interpreter as the client (`sys.executable`, `-m src.mcp.<server>`).

## Known limitations

- Free LLM tiers rate-limit by requests and tokens per minute. Use `LLM_MIN_INTERVAL`
  and `LLM_NUM_RETRIES`. If the provider fails, the filter reports how many
  articles it could not judge instead of treating them as "not relevant".
- The database is populated by the pipeline but the agents read markdown files;
  `SummarizerAgent` creates a `SearchSkill` that it does not use yet.
- `EnhancedFilterAgent` can call tools (`calculator`, and a mocked `web_search`),
  but in a full run over 43 articles with `gpt-oss-120b` the model never chose to
  call one. Its prompt is also looser than `NewsFilterAgent`'s (no examples), so
  it keeps more articles (13/43 against 9/43 in the runs we measured).
- The golden dataset is small (10 cases).

## Milestones

| Milestone | What was built |
|---|---|
| [M0 — Setup](docs/milestones/milestone-0-setup.md) | Dev environment, API key, verify script |
| [M1 — Async News Fetcher](docs/milestones/milestone-1-async-fetcher.md) | HackerNews and RSS fetchers, orchestrator, rate limiting |
| [M2 — SOLID Refactoring](docs/milestones/milestone-2-solid-refactoring.md) | SOLID principles, Factory/Strategy/Template Method, GitHub Trending added without editing existing code |
| [M3 — First Agent](docs/milestones/milestone-3-first-agent.md) | `NewsFilterAgent` via LiteLLM, tool calling |
| [M4 — MCP Pipeline](docs/milestones/milestone-4-mcp-pipeline.md) | Database MCP server, `SearchSkill`, three-agent pipeline |
| [M5 — Evaluation](docs/milestones/milestone-5-evaluation.md) | Golden dataset, metrics, documentation |

## License

MIT

## About the curriculum

This repository is part of Blend's 5-week AI engineering onboarding curriculum
(about 38–54 hours). Each milestone ends with a PR checkpoint reviewed by peers.
The curriculum overview lives in [`docs/curriculum/overview.md`](docs/curriculum/overview.md).
