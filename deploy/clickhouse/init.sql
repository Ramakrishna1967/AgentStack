-- AgentStack ClickHouse Schema
-- Schema Version: 2
-- Migration tracking via _schema_migrations table

-- Schema Migrations Table
-- Tracks which migrations have been applied
CREATE TABLE IF NOT EXISTS _schema_migrations (
    version UInt32,
    name String,
    applied_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree()
ORDER BY version;

-- Record initial schema version
INSERT INTO _schema_migrations (version, name) VALUES (1, 'initial_schema');

-- Spans Table (Core Telemetry)
-- Optimized for querying by project, trace, and time.
CREATE TABLE IF NOT EXISTS spans (
    span_id String,
    trace_id String,
    parent_span_id String,
    project_id String,
    name String,
    service_name String,
    status String, -- 'OK', 'ERROR', 'UNSET'
    start_time DateTime64(6), -- Microsecond precision
    end_time DateTime64(6),
    duration_ms Float64,
    attributes Map(String, String), -- Flat attributes (JSON strings for complex values)
    events String, -- JSON array of events
    ingested_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(start_time)
ORDER BY (project_id, service_name, start_time, trace_id, span_id)
TTL toDateTime(start_time) + INTERVAL 90 DAY;

-- Security Alerts Table
-- Stores threats detected by the Security Engine
CREATE TABLE IF NOT EXISTS security_alerts (
    id UUID DEFAULT generateUUIDv4(),
    project_id String,
    trace_id String,
    span_id String,
    rule_name String,
    severity Enum8('LOW' = 1, 'MEDIUM' = 2, 'HIGH' = 3, 'CRITICAL' = 4),
    score Float32, -- 0-100 threat score
    description String,
    evidence String, -- Excerpt causing the alert
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (project_id, severity, created_at);

-- Cost Metrics Table
-- Pre-aggregated cost data for fast analytics
CREATE TABLE IF NOT EXISTS cost_metrics (
    project_id String,
    model String,
    span_kind String, -- 'llm', 'embedding', etc.
    timestamp DateTime,
    prompt_tokens Int64,
    completion_tokens Int64,
    total_tokens Int64,
    cost_usd Float64
) ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (project_id, model, timestamp);
