#!/bin/sh

# Configuration
COLLECTOR_URL="http://agentstack-collector:4318/v1/traces"
API_KEY="ak_agentstack_demo_key_2026"
PROJECT_ID="demo-simulation"

trace_id=$(head /dev/urandom | tr -dc a-f0-9 | head -c 32)
span_id=$(head /dev/urandom | tr -dc a-f0-9 | head -c 16)
start_time=$(date +%s%N)
end_time=$((start_time + 500000000)) # +500ms

echo "Sending trace $trace_id..."

curl -X POST "$COLLECTOR_URL" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "resourceSpans": [{
        "resource": {
            "attributes": [
                {"key": "service.name", "value": {"stringValue": "shell-agent"}},
                {"key": "agentstack.project_id", "value": {"stringValue": "'$PROJECT_ID'"}}
            ]
        },
        "scopeSpans": [{
            "spans": [{
                "traceId": "'$trace_id'",
                "spanId": "'$span_id'",
                "name": "Shell Test Run",
                "kind": 1,
                "startTimeUnixNano": "'$start_time'",
                "endTimeUnixNano": "'$end_time'",
                "status": {"code": 1},
                "attributes": [{"key": "test.type", "value": {"stringValue": "shell"}}]
            }]
        }]
    }]
}'

echo "\n✅ Shell Simulation Sent."
