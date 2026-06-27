import time
import urllib.request
import json
import uuid

# Configuration
COLLECTOR_URL = "http://agentstack-collector:4318/v1/traces"
API_KEY = "ak_agentstack_demo_key_2026"
PROJECT_ID = "demo-simulation"

def send_span(name, trace_id=None, parent_id=None, status="OK", duration_ms=100):
    trace_id = trace_id or uuid.uuid4().hex
    span_id = uuid.uuid4().hex[:16]
    start_time_unix_nano = int(time.time() * 1e9)
    end_time_unix_nano = start_time_unix_nano + int(duration_ms * 1e6)
    
    payload = {
        "resourceSpans": [{
            "resource": {
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": "std-agent"}},
                    {"key": "agentstack.project_id", "value": {"stringValue": PROJECT_ID}}
                ]
            },
            "scopeSpans": [{
                "spans": [{
                    "traceId": trace_id,
                    "spanId": span_id,
                    "parentSpanId": parent_id if parent_id else "",
                    "name": name,
                    "kind": 1,
                    "startTimeUnixNano": str(start_time_unix_nano),
                    "endTimeUnixNano": str(end_time_unix_nano),
                    "status": {"code": 1 if status == "OK" else 2},
                    "attributes": [
                        {"key": "agentstack.status", "value": {"stringValue": status}}
                    ]
                }]
            }]
        }]
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(COLLECTOR_URL, data=data)
    req.add_header("Content-Type", "application/json")
    req.add_header("X-API-Key", API_KEY)
    
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Sent span '{name}': {response.status}")
    except Exception as e:
        print(f"Failed to send span '{name}': {e}")
        
    return trace_id, span_id

if __name__ == "__main__":
    print(" Starting AgentStack Standard Lib Simulation...")
    tid, sid = send_span("Standard Lib Test Run", duration_ms=500)
    print(f" Simulation Complete. Trace ID: {tid}")
