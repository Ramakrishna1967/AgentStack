import time
import requests
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
                    {"key": "service.name", "value": {"stringValue": "demo-agent"}},
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
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }
    
    response = requests.post(COLLECTOR_URL, json=payload, headers=headers)
    print(f"Sent span '{name}': {response.status_code}")
    return trace_id, span_id

if __name__ == "__main__":
    print("[INFO] Starting AgentStack Simulation...")
    # Complex trace
    tid, sid = send_span("User Input Processing", duration_ms=200)
    time.sleep(0.1)
    _, sid2 = send_span("Knowledge Retrieval", trace_id=tid, parent_id=sid, duration_ms=850)
    time.sleep(0.2)
    _, sid3 = send_span("LLM call (gpt-4o)", trace_id=tid, parent_id=sid2, duration_ms=1200)
    time.sleep(0.1)
    send_span("Output Generation", trace_id=tid, parent_id=sid3, status="OK", duration_ms=300)
    
    # Error trace
    print("\n[WARNING] Simulating Error Trace...")
    tid_e, sid_e = send_span("Secure Action", status="ERROR", duration_ms=50)
    
    print("\n[SUCCESS] Simulation Complete. Check Dashboard at http://localhost/")
