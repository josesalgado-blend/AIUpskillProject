# Deployment Guide

This project is designed to run **locally**. No cloud deployment is needed.

## Requirements

- Windows, macOS or Linux
- Python 3.11+
- An LLM provider API key (a free tier is enough, see [Configuration](#configuration))
- A few hundred MB of disk (the SQLite database and markdown files are small)

## Setup

See the [README](../README.md#installation) for installation. In short:

```bash
python -m venv venv
venv\Scripts\activate            # Windows  (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env             # then edit .env
python scripts/verify_setup.py
```

## Running

Always run from the **project root** and as a module (`-m`), so that `src` can be
imported. On Windows add `-X utf8` (the programs print emoji and read UTF-8 files).

```bash
python -X utf8 -m src.complete_pipeline
```

`python src/complete_pipeline.py` does **not** work: it fails with
`No module named 'src'`.

Output: `data/output/newsletter.md`, `data/context/` and `data/news_agent.db`.
A run over about 44 articles takes roughly 6 minutes on a free tier that needs
pacing (`LLM_MIN_INTERVAL=7`).

## Configuration

Environment variables, set in `.env` (git-ignored):

| Variable | Required | Description |
|---|---|---|
| `LITELLM_MODEL` | yes | Model string, e.g. `groq/openai/gpt-oss-120b` |
| `<PROVIDER>_API_KEY` | yes | Key for the provider of `LITELLM_MODEL` (`GROQ_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, ...) |
| `LLM_MIN_INTERVAL` | no | Seconds between LLM calls (default `0`); `7` for Groq's free tier |
| `LLM_NUM_RETRIES` | no | Retries on transient LLM errors (default `2`) |
| `ENVIRONMENT`, `LOG_LEVEL` | no | Present in `.env.example` |

Free tiers are enough for this project but have per-minute and per-day limits. A
full run makes about one LLM call per article plus one per topic and one for the
newsletter.

## Scheduling

> The scheduling commands below were written from the standard tools'
> documentation and were **not tested** in this repository.

### Windows (Task Scheduler)

1. Open Task Scheduler → **Create Basic Task**.
2. Trigger: **Daily**, at the time you want.
3. Action: **Start a program**.
4. Program/script: `C:\path\to\project\venv\Scripts\python.exe`
5. Add arguments: `-X utf8 -m src.complete_pipeline`
6. **Start in:** `C:\path\to\project` (required, otherwise `src` cannot be found)

### macOS / Linux (cron)

```bash
crontab -e
# every day at 9 AM
0 9 * * * cd /path/to/project && /path/to/project/venv/bin/python -m src.complete_pipeline >> logs/pipeline.log 2>&1
```

## Docker (optional, untested)

The repository does not include a Dockerfile and this one was **not built or
tested**. It shows the shape; note the command uses `-m`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "src.complete_pipeline"]
```

```bash
docker build -t aiupskillproject .
docker run --env-file .env -v "$(pwd)/data:/app/data" aiupskillproject
```

## Monitoring

The programs print progress to the console. To keep a log, redirect it:

```bash
mkdir logs
python -X utf8 -m src.complete_pipeline >> logs/pipeline.log 2>&1
```

Check the database without any extra tool:

```bash
python -c "import sqlite3; print(sqlite3.connect('data/news_agent.db').execute('SELECT COUNT(*) FROM articles').fetchone()[0])"
```

Look at the filter result: `data/context/filtered_articles.md` states the number of
articles it kept and, if something went wrong, how many it **could not judge**.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `ModuleNotFoundError: No module named 'src'` | Run from the project root with `python -m src.<module>`, not `python src/<file>.py` |
| `UnicodeDecodeError` / `UnicodeEncodeError` (`charmap`) on Windows | Add `-X utf8` (or set `PYTHONUTF8=1`) |
| `RateLimitError` / HTTP 429 | Free-tier limit. Set `LLM_MIN_INTERVAL` (e.g. `7`) and `LLM_NUM_RETRIES`, or wait for the daily quota to reset |
| `tenacity import failed` | Install dependencies again (`pip install -r requirements.txt`): `tenacity` is needed for retries |
| Filter reports "N articles could not be judged ... INCOMPLETE" | The provider failed for those articles (quota, network, invalid response). Re-run later; do not trust the result |
| Evaluation fails with "Evaluation invalid" | All test cases errored: check the API key, model and quota |
| MCP client hangs, or `No module named 'mcp'` in the server | The server was started with another Python, or printed to stdout. Servers must log to stderr and be launched with `sys.executable -m src.mcp.<server>` |
| `No module named 'bs4'` / `aiosqlite` | Install dependencies again with `pip install -r requirements.txt` |
