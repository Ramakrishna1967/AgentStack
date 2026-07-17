# Oxly SDK

Python instrumentation for [Oxly](https://github.com/ramakrishna1967/Oxly) — real-time tracing, security analysis, cost tracking, and Time Machine replay for AI agents built on **LangGraph**, **CrewAI**, **AutoGen**, or custom Python.

Oxly runs as **one FastAPI process** backed by **SQLite** — no Redis, no ClickHouse, no separate Collector or Workers to deploy. This SDK talks directly to that process over HTTPS, with a local SQLite fallback if it's unreachable.

## Install

```bash
pip install oxly
```

## Quickstart

**1. Run the Oxly API** (see the [main README](https://github.com/ramakrishna1967/Oxly#running-it) for the full walkthrough — no Docker, Redis, or ClickHouse required):

```bash
git clone https://github.com/ramakrishna1967/Oxly
cd Oxly
pip install -e packages/api
export JWT_SECRET_KEY=$(openssl rand -hex 32)
export DATABASE_URL="sqlite+aiosqlite:///oxly.db"
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

**2. Instrument your agent:**

```python
from oxly import observe, init

init(
    collector_url="http://localhost:8000",  # your running Oxly API
    api_key="ak_your_project_key",          # from POST /api/v1/projects
)

@observe
def research_agent(query: str) -> str:
    context = search_tool(query)
    return llm.chat(f"Answer based on: {context}")

@observe(name="planning.step")
async def async_agent(objective: str) -> list[str]:
    return await llm.achat(f"Break this into steps: {objective}")
```

Every call produces a full trace — arguments, return values, timing, exceptions, token counts, and cost — visible in the dashboard at `http://localhost:8000`.

> **Zero-interference guarantee.** `@observe` will never crash your application. If Oxly hits an internal error, your function runs normally and the SDK fails silently.

## Configuration

`init()` accepts explicit kwargs, or falls back to `OXLY_*` environment variables (`OXLY_API_KEY`, `OXLY_COLLECTOR_URL`, `OXLY_ENABLED`, `OXLY_SERVICE_NAME`, `OXLY_DEBUG`, ...). See `oxly.config.OxlyConfig` for the full list and defaults.

## License

Apache 2.0
