# AgentStack
---

## 1. What Is AgentStack?

AgentStack is an **open-source, self-hosted observability platform purpose-built for AI agents**.
Traditional APM tools (Datadog, New Relic) are designed for web services with millisecond-range,
deterministic request/response cycles. AI agents are fundamentally different: they run for
minutes/hours, make non-deterministic LLM calls, accumulate variable per-token costs, and
handle sensitive conversational text.

AgentStack solves this with:

| Capability | Description |
|---|---|
| **Real-time Tracing** | Auto-captures every LLM call, tool invocation, and function execution as structured spans forming a tree |
| **Time Machine Replay** | Step through any past agent execution span-by-span for debugging |
| **Security Engine** | Detects prompt injection, PII leakage, jailbreaks, and token explosions in real time |
| **PII Sanitization** | Auto-scrubs SSNs, credit cards, emails, API keys, phone numbers before storage |
| **Cost Analytics** | Per-model token counting + USD cost calculation with timeseries charts |
| **Framework Auto-Detection** | Native hooks for LangGraph, CrewAI, AutoGen + generic Python support |
| **Offline Resilience** | Spans buffer to local SQLite if the collector is unreachable, and auto-replay on reconnect |

**GitHub:** `https://github.com/Ramakrishna1967/AgentState`
**License:** Apache 2.0

---

## 2. High-Level Architecture

```
  Your Application (Python)
  ( @observe decorator from SDK )
          |
          |  HTTPS  (gzip, exponential backoff)
          v
  +-------------------------------+
  |   Collector   (FastAPI)       |   Validates API keys, enforces 5MB payload limits,
  |   Port 4318                   |   and pushes validated spans to Redis Streams
  +---------------+---------------+
                  |
                  v  Redis Streams channel: "spans.ingest"
                  |
       +----------+----------+
       |          |          |
  ClickHouse  Security    Cost
   Writer      Engine    Calculator
       |          |          |
       +----------+----------+
                  |
         ClickHouse DB
         ┌─────────────────┐
         │ spans            │  (MergeTree, 90-day TTL)
         │ security_alerts  │  (MergeTree)
         │ cost_metrics     │  (SummingMergeTree)
         └─────────────────┘
                  |
          API Server (FastAPI)
          REST + WebSocket + JWT
          Port 8000
                  |
     Dashboard (React 19 + TypeScript + Vite)
     Pages: Dashboard | TraceView | Analytics | Security | Settings
```

**Data Flow Summary:**
1. SDK `@observe` wraps user functions → creates `SpanModel` objects
2. SDK batches spans and POSTs gzip-compressed JSON to Collector at `/v1/traces`
3. Collector authenticates via SHA-256 hashed API key lookup, validates payload, pushes to Redis Stream `spans.ingest`
4. Three independent Workers consume from Redis concurrently:
   - **ClickHouse Writer** — persists raw spans to `spans` table
   - **Security Engine** — runs detection rules (injection, anomaly, PII) → writes `security_alerts`
   - **Cost Calculator** — extracts `llm.model`/`llm.tokens.*` attributes → writes `cost_metrics`
5. API Server queries ClickHouse for analytics + SQLite for user/project/auth data
6. Dashboard fetches via REST API + receives live updates via WebSocket

---

## 3. Technology Stack

| Layer | Technology | Version |
|---|---|---|
| SDK | Python, Pydantic v2 | Python 3.10+ |
| Collector | FastAPI, Redis | — |
| Workers | Python, Redis Streams | — |
| API Server | FastAPI, SQLite (aiosqlite), ClickHouse (httpx) | — |
| Dashboard | React 19, TypeScript 5.9, Vite, Recharts | Node 18+ |
| Infrastructure | Redis 7, ClickHouse 24.3, Nginx (Alpine) | Docker Compose |
| CI/CD | GitHub Actions, Bandit, flake8, pytest, TypeScript tsc | — |

---

## 4. Complete File Tree with Module Purposes

### 4.1 `packages/sdk-python/` — The Python SDK

Users install this via `pip install agentstack`.

```
packages/sdk-python/
├── pyproject.toml                    # Package metadata (hatchling build backend)
├── Makefile                          # Dev shortcuts: make test, make lint
├── src/agentstack/
│   ├── __init__.py                   # Public API: observe(), init(), Tracer, Span, __version__
│   ├── config.py                     # AgentStackConfig (Pydantic Settings, reads AGENTSTACK_* env vars)
│   ├── models.py                     # Pydantic v2 models: SpanModel, TraceModel, SpanEvent, SpanStatus
│   ├── tracer.py                     # Tracer singleton — creates/manages Span objects, builds span tree
│   ├── context.py                    # Thread-safe context propagation using contextvars (stores current span)
│   ├── decorator.py                  # @observe implementation — wraps sync/async functions, creates spans
│   ├── sanitizer.py                  # PII scrubber — regex-based removal of SSNs, credit cards, emails, etc.
│   ├── exporter.py                   # Serializes spans to JSON, applies sanitizer, hands to transport
│   ├── local_store.py                # SQLite offline buffer — stores spans when collector unreachable
│   ├── _internal/
│   │   ├── buffer.py                 # In-memory span batch buffer with flush interval
│   │   ├── transport.py              # HTTP transport layer — gzip, exponential backoff, retry logic
│   │   └── clock.py                  # Nanosecond-precision timestamps (time.time_ns())
│   └── frameworks/
│       ├── __init__.py               # Auto-detection logic: checks which frameworks are importable
│       ├── langraph.py               # LangGraph-specific hooks (patches StateGraph nodes)
│       ├── crewai.py                 # CrewAI-specific hooks (patches Agent.execute)
│       └── autogen.py                # AutoGen-specific hooks (patches ConversableAgent)
└── tests/                            # pytest tests with asyncio support
```

**Key Design Decisions:**
- `@observe` NEVER crashes the user's app. Exceptions in telemetry are silently swallowed.
- `observe()` supports both `@observe` and `@observe(name="custom")` syntax.
- Context propagation uses Python's `contextvars` — thread-safe and async-safe.
- All timestamps are nanosecond-precision integers (not datetime objects).

### 4.2 `packages/collector/` — Ingestion Server

```
packages/collector/
├── Dockerfile
├── pyproject.toml
└── src/collector/
    ├── __init__.py
    ├── server.py           # FastAPI app — POST /v1/traces endpoint, CORS, middleware
    ├── auth.py             # API key authentication — SHA-256 hash lookup against SQLite
    ├── validators.py       # Payload validation — size limits (5MB), schema checks
    ├── redis_writer.py     # Pushes validated spans to Redis Stream "spans.ingest"
    ├── health.py           # GET /health endpoint with dependency checks
    └── config.py           # Environment config (REDIS_URL, ALLOWED_ORIGINS)
```

**Key Design Decisions:**
- API key auth uses two tiers: SHA-256 hash for fast in-memory cache, pbkdf2_sha256 for first-use verification.
- Payload body size is enforced at the middleware level (5MB hard limit).
- CORS allowlist is explicit (no wildcards) and credentials are disabled.

### 4.3 `packages/workers/` — Background Stream Processors

```
packages/workers/
├── Dockerfile
├── pyproject.toml
└── src/workers/
    ├── __init__.py
    ├── consumer.py              # Base Redis Streams consumer (XREADGROUP, ACK, retry logic)
    ├── clickhouse_writer.py     # Batch-inserts spans into ClickHouse "spans" table
    ├── security_engine.py       # Runs all detection rules on each span, writes security_alerts
    ├── cost_calculator.py       # Extracts llm.model + token counts, calculates USD cost, writes cost_metrics
    └── rules/
        ├── __init__.py          # Rule registry — collects all rule functions
        ├── injection.py         # Prompt injection detection (regex patterns for "ignore previous", etc.)
        ├── anomaly.py           # Anomaly detection (excessive tokens, unusual latency spikes)
        └── pii.py               # PII detection (flags spans containing unredacted PII)
```

**Key Design Decisions:**
- Each worker is a separate process (separate container in Docker).
- Workers use Redis consumer groups — if one crashes, pending messages aren't lost.
- Security rules are modular: each rule file exports functions that take a span dict and return alerts.

### 4.4 `packages/api/` — REST API & WebSocket Server

```
packages/api/
├── Dockerfile
├── pyproject.toml
├── .env / .env.example
└── src/api/
    ├── __init__.py
    ├── main.py              # FastAPI app factory — registers routes, CORS, startup events
    ├── config.py            # Settings via environment variables (SECRET_KEY, DATABASE_URL, etc.)
    ├── db.py                # SQLite async ORM (aiosqlite) — users, projects, api_keys tables
    ├── db_clickhouse.py     # ClickHouse HTTP client (httpx) — queries spans/alerts/cost tables
    ├── schemas.py           # Pydantic v2 request/response schemas (mirrors SDK models exactly)
    ├── middleware.py         # Rate limiting (100 req/min/IP), request logging
    ├── dependencies.py      # FastAPI Depends() — JWT extraction, current user injection
    └── routes/
        ├── __init__.py      # Router aggregation
        ├── auth.py          # POST /register, POST /login → JWT (24h expiry), brute-force lockout
        ├── projects.py      # CRUD for projects + API key generation (shown once)
        ├── traces.py        # GET /traces (paginated list), GET /traces/{id} (full span tree for Time Machine)
        ├── spans.py         # GET /spans (query by trace_id, project_id)
        ├── analytics.py     # GET /analytics/cost, /analytics/tokens — timeseries data from ClickHouse
        ├── security.py      # GET /security/alerts — paginated security alerts
        └── ws.py            # WebSocket /ws/traces — pushes new traces to dashboard in real time
```

**Key Design Decisions:**
- User/project/auth data lives in SQLite (lightweight, no extra infra needed).
- Telemetry data lives in ClickHouse (optimized for analytical queries).
- Password hashing uses pbkdf2_sha256 with salt.
- Brute-force protection: 5 failed logins per email per 15 minutes → lockout.

### 4.5 `packages/dashboard/` — React Frontend

```
packages/dashboard/
├── Dockerfile
├── package.json             # React 19, TypeScript, Vite, react-router-dom, recharts, lucide-react
├── vite.config.ts
├── index.html
├── tsconfig*.json
└── src/
    ├── main.tsx             # React root with BrowserRouter
    ├── App.tsx              # Top-level layout + routes (/, /traces/:id, /analytics, /security, /settings)
    ├── App.css
    ├── index.css
    ├── styles/
    │   └── globals.css      # Global design system — BRUTALIST/HACKER aesthetic (black, neon green, monospace)
    ├── lib/
    │   ├── types.ts         # TypeScript interfaces: Span, Trace, TraceDetail, SecurityAlert, Project, User
    │   ├── api.ts           # Axios/fetch wrapper pointing to VITE_API_URL
    │   └── utils.ts         # Formatting helpers (duration, timestamps, truncation)
    ├── hooks/
    │   ├── useTraces.ts     # Data-fetching hook for traces list
    │   ├── useProject.ts    # Current project context
    │   └── useWebSocket.ts  # WebSocket hook for live trace feed
    ├── components/
    │   ├── TraceTimeline.tsx       # Gantt-chart-style waterfall view of spans in a trace
    │   ├── SpanDetail.tsx          # Span attribute inspector panel
    │   ├── ReplayViewer.tsx        # TIME MACHINE — step-by-step span replay UI (flagship feature)
    │   ├── TraceSearch.tsx         # Search/filter bar for traces
    │   ├── LiveFeed.tsx            # Real-time trace arrival feed via WebSocket
    │   ├── CostChart.tsx           # Recharts cost timeseries
    │   ├── TokenUsageChart.tsx     # Token usage bar/line chart
    │   ├── TraceLatencyChart.tsx   # Latency distribution chart
    │   ├── SecurityPanel.tsx       # Security alert list with severity badges
    │   ├── SecurityMetricsChart.tsx# Security severity distribution chart
    │   └── ProjectSwitcher.tsx     # Project dropdown selector
    └── pages/
        ├── Dashboard.tsx    # Overview page — metrics cards, live feed, charts
        ├── TraceView.tsx    # Individual trace deep-dive + Time Machine replay
        ├── Analytics.tsx    # Cost & token analytics with charts
        ├── Security.tsx     # Security alerts page
        └── Settings.tsx     # User settings + API key management
```

**Design Aesthetic:** "Brutalist / Hacker" — black backgrounds, neon green (#00ff41) accents,
monospace fonts (JetBrains Mono / Source Code Pro), sharp 1px borders, no rounded corners,
no glassmorphism. Terminal-like feel.

### 4.6 `deploy/` — Infrastructure

```
deploy/
├── docker-compose.yml       # 8 services: redis, clickhouse, api, collector, 3 workers, dashboard, nginx
├── .env.example             # Template: DATABASE_URL, REDIS_URL, SECRET_KEY, etc.
├── nginx/
│   └── default.conf         # Reverse proxy — routes /api→api:8000, /collect→collector:4318, /→dashboard
├── redis/
│   └── redis.conf           # Password auth, maxmemory, persistence config
└── clickhouse/
    └── init.sql             # Schema: spans, security_alerts, cost_metrics tables
```

### 4.7 Other Top-Level Files

```
.github/workflows/
├── ci.yml                   # On push/PR: lint, bandit scan, pytest (3.10/3.11/3.12), dashboard build
└── release.yml              # On tag v*: build SDK → publish to PyPI, build Docker images → push to Docker Hub

scripts/
├── benchmark.py             # Performance benchmarking for SDK overhead
├── seed_data.py             # Populates ClickHouse with synthetic data for demos
├── demo_crewai.py           # CrewAI integration example
└── demo_autogen.py          # AutoGen integration example

examples/
└── demo_agent.py            # LangGraph demo with prompt injection simulation

tests/                       # Integration tests

LICENSE                      # Apache 2.0
README.md                    # Project README (users see this on GitHub)
.gitignore
```

---

## 5. Database Schemas

### 5.1 ClickHouse — `spans`
```sql
CREATE TABLE spans (
    span_id         String,
    trace_id        String,
    parent_span_id  String,
    project_id      String,
    name            String,
    service_name    String,
    status          String,            -- 'OK' | 'ERROR' | 'UNSET'
    start_time      DateTime64(6),     -- Microsecond precision
    end_time        DateTime64(6),
    duration_ms     Float64,
    attributes      Map(String, String),
    events          String,            -- JSON array
    ingested_at     DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(start_time)
ORDER BY (project_id, service_name, start_time, trace_id, span_id)
TTL start_time + INTERVAL 90 DAY;
```

### 5.2 ClickHouse — `security_alerts`
```sql
CREATE TABLE security_alerts (
    id          UUID DEFAULT generateUUIDv4(),
    project_id  String,
    trace_id    String,
    span_id     String,
    rule_name   String,
    severity    Enum8('LOW'=1, 'MEDIUM'=2, 'HIGH'=3, 'CRITICAL'=4),
    score       Float32,       -- 0-100 threat score
    description String,
    evidence    String,        -- Excerpt that triggered the alert
    created_at  DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (project_id, severity, created_at);
```

### 5.3 ClickHouse — `cost_metrics`
```sql
CREATE TABLE cost_metrics (
    project_id        String,
    model             String,
    span_kind         String,      -- 'llm', 'embedding', etc.
    timestamp         DateTime,
    prompt_tokens     Int64,
    completion_tokens Int64,
    total_tokens      Int64,
    cost_usd          Float64
) ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (project_id, model, timestamp);
```

### 5.4 SQLite — Managed by API (`db.py`)
- **users** — id, email, password_hash, is_active, created_at, failed_login_attempts, locked_until
- **projects** — id, name, owner_id (FK→users), created_at, updated_at
- **api_keys** — id, project_id (FK→projects), key_hash (SHA-256), key_prefix ("ak_..."), created_at

---

## 6. Core Data Models (Pydantic v2)

### SDK Side (`packages/sdk-python/src/agentstack/models.py`)

```python
class SpanStatus(str, Enum):
    OK = "OK"
    ERROR = "ERROR"

class SpanEvent(BaseModel):
    name: str
    timestamp: int          # Nanoseconds since epoch
    attributes: dict[str, str]

class SpanModel(BaseModel):
    trace_id: str           # UUID grouping all spans in one execution
    span_id: str            # Unique ID for this operation
    parent_span_id: str | None
    name: str               # e.g. "llm.chat", "tool.call", "langgraph.node.X"
    start_time: int         # Nanoseconds
    end_time: int
    duration_ms: int
    status: SpanStatus
    service_name: str
    attributes: dict[str, str]   # "llm.model", "llm.tokens.in", "tool.name", etc.
    events: list[SpanEvent]
    project_id: str
    api_key_hash: str
```

### Commonly Used Span Attributes
| Attribute Key | Example Value | Set By |
|---|---|---|
| `llm.model` | `"gpt-4-turbo"` | User/framework hook |
| `llm.tokens.in` | `"450"` | User/framework hook |
| `llm.tokens.out` | `"120"` | User/framework hook |
| `tool.name` | `"vector_db_search"` | User/framework hook |
| `input_payload` | `"Query text..."` | User |
| `output_payload` | `"Result text..."` | User |
| `framework` | `"langgraph"` | Auto-detection |

---

## 7. API Endpoints

### Auth
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/register` | None | Create user account |
| POST | `/login` | None | Get JWT token (24h expiry) |

### Projects
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/projects` | JWT | List user's projects |
| POST | `/projects` | JWT | Create project → returns API key (shown once) |

### Traces
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/traces` | JWT | Paginated trace list for a project |
| GET | `/traces/{trace_id}` | JWT | Full span tree (used by Time Machine) |

### Spans
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/spans` | JWT | Query spans by trace_id / project_id |

### Analytics
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/analytics/cost` | JWT | Cost timeseries data |
| GET | `/analytics/tokens` | JWT | Token usage timeseries |

### Security
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/security/alerts` | JWT | Paginated security alerts |

### WebSocket
| Path | Auth | Description |
|---|---|---|
| `/ws/traces` | JWT (query param) | Live push of new traces as they arrive |

### Collector
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/v1/traces` | API Key | SDK span ingestion endpoint |
| GET | `/health` | None | Health check |

---

## 8. Security Architecture

| Layer | Implementation |
|---|---|
| **Container Security** | All Docker images run as non-root `appuser` |
| **Secrets** | Environment variables only; `.env` is gitignored |
| **Auth** | JWT (HS256, 24h expiry) + pbkdf2_sha256 password hashing |
| **API Key Auth** | SHA-256 in-memory cache for hot path; pbkdf2 on first use |
| **Brute Force** | 5 failed logins per email per 15 min → account lockout |
| **Rate Limiting** | 100 requests/minute per IP (API middleware) |
| **CORS** | Explicit origin allowlist; credentials disabled on Collector |
| **Payload Limits** | 5MB hard limit enforced at middleware level |
| **PII Sanitization** | Regex-based scrub of SSNs, credit cards, emails, phone numbers, AWS keys, OpenAI keys |
| **CI Scanning** | Bandit static analysis runs on every push/PR |

---

## 9. How to Run Locally

### Option A: Docker Compose (Recommended)
```bash
cd deploy/
cp .env.example .env       # Edit SECRET_KEY
docker compose up -d --build
# Dashboard: http://localhost:80
# API: http://localhost:8000
# Collector: http://localhost:4318
```

### Option B: Manual (each in separate terminal)
```bash
# 1. Start Redis + ClickHouse (via Docker or native installs)

# 2. API Server
pip install -e packages/api
uvicorn api.main:app --host 0.0.0.0 --port 8000

# 3. Collector
pip install -e packages/collector
uvicorn collector.server:app --host 0.0.0.0 --port 4318

# 4. Workers (each in separate terminal)
pip install -e packages/workers
python -m workers.clickhouse_writer
python -m workers.security_engine
python -m workers.cost_calculator

# 5. Dashboard
cd packages/dashboard && npm install && npm run dev
# → http://localhost:5173
```

### Send Test Traces
```bash
pip install -e packages/sdk-python
pip install langgraph
python examples/demo_agent.py
```

---

## 10. Coding Conventions

| Convention | Rule |
|---|---|
| **Python version** | 3.10+ (uses `X | Y` union syntax, no `Optional[X]`) |
| **Models** | Pydantic v2 `BaseModel` with `Field()` descriptions |
| **Async** | API + Collector use `async def` everywhere; Workers are synchronous |
| **Imports** | `from __future__ import annotations` at top of every file |
| **Linting** | Ruff (rules: E, F, W, I, N, UP, B, A, SIM, TCH), line length 100 |
| **Testing** | pytest + pytest-asyncio, `asyncio_mode = "auto"` |
| **License** | Every file starts with `# Copyright 2026 AgentStack Contributors` + SPDX |
| **Frontend** | React 19 functional components, TypeScript strict, CSS-in-globals (no Tailwind) |
| **CSS** | Brutalist/Hacker aesthetic: black bg, neon green (#00ff41), monospace fonts, 1px borders |
| **Error handling** | SDK: never raise; Backend: raise `HTTPException`; Workers: log + NACK |

---

## 11. Environment Variables

| Variable | Used By | Description |
|---|---|---|
| `SECRET_KEY` | API | JWT signing key (HS256) |
| `DATABASE_URL` | API, Collector | SQLite connection string |
| `REDIS_URL` | Collector, Workers | Redis connection (with password) |
| `REDIS_PASSWORD` | Docker Compose | Redis AUTH password |
| `CLICKHOUSE_HOST` | API, Workers | ClickHouse hostname |
| `CLICKHOUSE_PORT` | API, Workers | ClickHouse HTTP port (default 8123) |
| `CLICKHOUSE_PASSWORD` | Docker Compose, Workers | ClickHouse auth |
| `ALLOWED_ORIGINS` | Collector | CORS allowlist (comma-separated) |
| `VITE_API_URL` | Dashboard | API base URL for frontend |
| `VITE_WS_URL` | Dashboard | WebSocket URL for live feed |
| `AGENTSTACK_API_KEY` | SDK | API key for trace authentication |
| `AGENTSTACK_COLLECTOR_URL` | SDK | Collector endpoint URL |
| `AGENTSTACK_ENABLED` | SDK | Enable/disable telemetry ("true"/"false") |
| `AGENTSTACK_SERVICE_NAME` | SDK | Service name for spans |
| `AGENTSTACK_DEBUG` | SDK | Enable debug logging |

---

## 12. Pending / Known Issues

1. **PyPI Publishing** — Package name in `pyproject.toml` is `agentstack-sdk`; needs renaming to `agentstack` for `pip install agentstack`. Version string `0.1.0-alpha` is not PEP 440 compliant (should be `0.1.0a1`).
2. **`release.yml` Paths** — Working directory uses `agentstack/packages/sdk-python` (wrong nesting); should be `packages/sdk-python`.
3. **Project URLs** — `pyproject.toml` links to `github.com/agentstack/agentstack` instead of `github.com/Ramakrishna1967/AgentState`.
4. **No SDK README** — PyPI page needs a standalone README at `packages/sdk-python/README.md`.
5. **No `CONTRIBUTING.md`** or `ISSUE_TEMPLATE` for open-source contributors.

---

*Last updated: 2026-02-26*
