<div align="center">

<br>

# Agentstack

### The open-source observability platform for AI agents

<br>

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg?style=flat-square)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6.svg?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![ClickHouse](https://img.shields.io/badge/ClickHouse-24.3-FFCC01.svg?style=flat-square&logo=clickhouse&logoColor=black)](https://clickhouse.com)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](https://github.com/agentstack/agentstack/pulls)

AgentStack gives you **real-time tracing, security analysis, cost tracking, and Time Machine replay** for AI agents — without changing how you build them.

Works with **LangGraph** &nbsp;&middot;&nbsp; **CrewAI** &nbsp;&middot;&nbsp; **AutoGen** &nbsp;&middot;&nbsp; **Custom Python**

<br>

[Get Started](#get-started) &nbsp;&bull;&nbsp;
[Why AgentStack](#why-agentstack) &nbsp;&bull;&nbsp;
[Features](#features) &nbsp;&bull;&nbsp;
[Architecture](#architecture) &nbsp;&bull;&nbsp;
[Deployment](#deployment) &nbsp;&bull;&nbsp;
[Contributing](#contributing)

<br>

---

</div>

<br>

## Get Started

**1. Install the SDK**

```bash
pip install agentstate-sdk
```

**2. Instrument your agent with one decorator**

```python
from agentstack import observe, init

init(
    collector_url="https://your-collector.example.com",
    api_key="ak_your_project_key",
)

@observe
def research_agent(query: str) -> str:
    context = search_tool(query)
    return llm.chat(f"Answer based on: {context}")

@observe(name="planning.step")
async def async_agent(objective: str) -> list[str]:
    return await llm.achat(f"Break this into steps: {objective}")
```

Every call now produces a full trace — arguments, return values, timing, exceptions, token counts, and cost — visible instantly in the dashboard.

> **Zero-interference guarantee.** The `@observe` decorator will never crash your application. If AgentStack encounters an internal error, your function executes normally and the SDK fails silently.

<br>

## Why AgentStack

Most observability tools are designed for web services. AI agents have fundamentally different requirements:

| Challenge | Web Services | AI Agents | AgentStack |
|-----------|:---:|:---:|---|
| **Request duration** | Milliseconds | Minutes to hours | Durable traces with offline fallback |
| **Cost** | Fixed infra | Variable per-token billing | Per-model cost tracking with timeseries |
| **Security** | Known attack vectors | Prompt injection, PII leakage | Real-time detection engine |
| **Debugging** | Deterministic stack traces | Non-deterministic LLM behavior | Time Machine — step-by-step replay |
| **Data sensitivity** | Headers and bodies | Full conversation text | Auto-PII sanitization before export |
| **Call structure** | Flat request/response | Deep nested trees (agent → tool → LLM → tool) | Automatic parent-child span linking |

<br>

## Features

<table>
<tr>
<td width="50%" valign="top">

**Real-time Tracing**

Automatically capture every LLM call, tool invocation, and function execution as a structured span. Supports sync, async, and deeply nested call chains with zero manual instrumentation beyond `@observe`.

</td>
<td width="50%" valign="top">

**Time Machine Replay**

Step through any past agent execution span-by-span. See exactly which LLM calls were made, what each tool returned, and which decision path was taken — without reproducing the failure.

</td>
</tr>
<tr>
<td width="50%" valign="top">

**Security Engine**

Detect prompt injection, PII leakage, and anomalous behavior in real time. Security alerts (jailbreak patterns, token explosions, excessive latency) surface in the dashboard within seconds of occurring.

</td>
<td width="50%" valign="top">

**Automatic PII Sanitization**

Every span is scrubbed before export. SSNs, credit card numbers, emails, phone numbers, AWS keys, and OpenAI keys are detected and redacted automatically — no config required.

</td>
</tr>
<tr>
<td width="50%" valign="top">

**Cost Analytics**

Per-model token counting and USD cost calculation with timeseries charts. Track spend across GPT-4, Claude, Gemini, and any other provider — broken down by hour, day, or week.

</td>
<td width="50%" valign="top">

**Framework Auto-Detection**

Native hooks for **LangGraph**, **CrewAI**, and **AutoGen**. AgentStack detects your framework at import time and instruments the right entry points automatically.

</td>
</tr>
<tr>
<td width="50%" valign="top">

**Offline Resilience**

If the collector is unreachable, spans are written to a local SQLite store and replayed automatically when connectivity is restored. No data is lost due to network failures.

</td>
<td width="50%" valign="top">

**Production Hardened**

Non-root containers, JWT auth with brute-force lockout, SHA-256 API key caching, 5MB payload limits, CORS allowlists, per-IP rate limiting, and Bandit security scanning in CI.

</td>
</tr>
</table>

<br>

## Architecture

```
  Your Application
  ( @observe decorator )
         |
         |  HTTPS  (gzip-compressed, exponential backoff retry)
         v
  +-------------------------------+
  |   Collector   (FastAPI)       |   Validates API keys, enforces payload limits,
  |   Port 4318                   |   and writes spans to Redis Streams
  +---------------+---------------+
                  |
                  v  Redis Streams  (spans.ingest)
                  |
       +----------+----------+
       |          |          |
  ClickHouse  Security    Cost
   Writer      Engine    Calculator
       |          |          |
       +----------+----------+
                  |
         ClickHouse (spans / security_alerts / cost_metrics)
                  |
          API Server (FastAPI)
          REST + WebSocket + JWT
                  |
     Dashboard (React + TypeScript)
     Traces | Analytics | Security
```

**Components at a glance:**

| Package | Stack | Role |
|---------|-------|------|
| `packages/sdk-python` | Python 3.10+, Pydantic v2 | `@observe` decorator, context propagation, PII scrubber, batching, transport |
| `packages/collector` | FastAPI, Redis | Ingestion endpoint — validates, authenticates, and streams spans |
| `packages/workers` | Python, Redis Streams | Three independent processors: ClickHouse writer, security engine, cost calculator |
| `packages/api` | FastAPI, SQLite, ClickHouse | REST API, WebSocket live feeds, JWT auth, trace replay |
| `packages/dashboard` | React 19, TypeScript, Vite, Recharts | Real-time trace viewer, analytics, Time Machine, security alerts |
| `deploy/` | Redis 7, ClickHouse 24.3, Nginx | Infrastructure configs, Docker Compose, health checks |

<br>

## Project Structure

```
.
├── packages/
│   ├── sdk-python/        # Python SDK (pip install agentstack-sdk)
│   ├── collector/         # Trace ingestion server
│   ├── workers/           # Background stream processors
│   ├── api/               # REST API and WebSocket server
│   └── dashboard/         # React frontend
│
├── deploy/
│   ├── docker-compose.yml
│   ├── nginx/
│   ├── redis/
│   └── clickhouse/
│
├── tests/                 # Integration tests
├── examples/              # Example agent scripts
├── .github/workflows/     # CI — lint, typecheck, bandit, build
├── LICENSE
└── README.md
```

<br>

## Deployment

AgentStack is fully self-hostable. Deploy the complete stack with Docker Compose:

```bash
git clone https://github.com/ramakrishna1967/AgentStack
cd agentstack

# Copy and configure secrets
cp .env.example .env

# Start the full stack
docker compose up -d
```

The stack starts 8 containers: Redis, ClickHouse, Collector, API, three Workers, and the Dashboard — all with health checks and memory limits.

**Environment variables required:**

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing secret — generate with `openssl rand -hex 32` |
| `REDIS_PASSWORD` | Redis authentication password |
| `CLICKHOUSE_PASSWORD` | ClickHouse database password |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed CORS origins |

Once running, point the SDK at your collector:

```python
from agentstack import init

init(
    collector_url="https://collector.yourdomain.com",
    api_key="ak_your_key",
)
```

<br>

## Security

| Layer | Details |
|-------|---------|
| **Containers** | All images run as non-root `appuser` |
| **Secrets** | Environment variables only; `.env` is gitignored |
| **Auth** | JWT (24h expiry) + pbkdf2_sha256 password hashing |
| **API Keys** | SHA-256 cache on hot path; pbkdf2 on first use |
| **Brute force** | 5 failed logins per email per 15 minutes triggers lockout |
| **Rate limiting** | 100 requests/minute per IP |
| **CORS** | Explicit allowlist; credentials disabled on Collector |
| **Payloads** | 5MB limit enforced on actual request body |
| **CI scanning** | Bandit static analysis on every PR |
| **PII** | Scrubbed from every span before storage |

To report a security vulnerability, please open a [GitHub Security Advisory](https://github.com/agentstack/agentstack/security/advisories/new) rather than a public issue.

<br>

## Contributing

Contributions are welcome — from bug reports and docs improvements to new framework integrations and features.

**Development setup:**

```bash
# Python SDK
cd packages/sdk-python
pip install -e ".[dev]"
make test      # Run tests with coverage
make lint      # Ruff linter

# Dashboard
cd packages/dashboard
npm install
npm run dev    # Dev server with hot reload
npm run build  # Production build + TypeScript check

# Full stack
cd deploy
docker compose up -d
```

Please open an issue before starting on significant changes so we can discuss the approach together.

<br>

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.

Copyright 2026 AgentStack Contributors.

---

<div align="center">
<br>
If AgentStack is useful to you, please consider giving it a star. It helps others find the project.
<br><br>
</div>
