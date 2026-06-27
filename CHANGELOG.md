# Changelog

All notable changes to AgentStack are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Security
- Removed hardcoded Redis password from `redis.conf`; password now injected at runtime via entrypoint script
- Fixed auth bypass: JWT with non-existent `sub` no longer falls back to demo user
- Added authentication to `GET /projects`, `GET /projects/{id}`, `GET /traces`, `GET /traces/{trace_id}`, `GET /spans/{id}`, `GET /analytics/cost`, `GET /security/alerts`
- Scoped project listing to authenticated user via `user_projects` table
- Blocked collector from accepting caller-supplied `project_id` in span payload
- Added decompressed size limit (50MB) after gzip inflate to prevent gzip bomb OOM
- Added `OPENAI_KEY_V2`, `ANTHROPIC_KEY`, `HUGGINGFACE_TOKEN` patterns to PII detector
- Added rate limiting middleware to collector endpoint
- Redis and ClickHouse ports now bind to `127.0.0.1` instead of `0.0.0.0`

### Fixed
- `get_trace_replay` endpoint now queries ClickHouse (was querying empty SQLite spans table)
- Added missing `import time` in `traces.py`
- Redis URL no longer logged with embedded password
- ClickHouse writer buffer capped at 50,000 entries to prevent OOM on CH outage
- DLQ stream now has `MAXLEN=100,000` and stores error reason per message
- `alerts.live` Redis stream now has `MAXLEN=10,000`
- CI pytest step now fails the job on test failure (was silenced with `|| echo`)

### Changed
- Docker Compose: all services use `condition: service_healthy` in `depends_on`
- Docker Compose: added ClickHouse healthcheck
- Docker Compose: added healthchecks to all three worker containers
- Pricing table updated with current models: `gpt-4o-mini`, `claude-3-5-sonnet`, `claude-3-5-haiku`, `claude-opus-4`, `claude-sonnet-4`, Gemini 1.5/2.0, embedding models

### Added
- `SECURITY.md` — vulnerability disclosure policy
- `CONTRIBUTING.md` — contributor guide
- `mypy` type checking added to CI

## [0.1.0-alpha] - 2026-06-27

### Added
- Initial release
- `@observe` decorator for LangGraph, CrewAI, AutoGen, and custom Python agents
- Real-time trace streaming via WebSocket
- Security engine: prompt injection and PII detection
- Cost tracking per model and project
- Time Machine trace replay
- Self-hosted Docker Compose deployment
