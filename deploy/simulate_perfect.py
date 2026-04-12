import time
import urllib.request
import json
import uuid

# Configuration
COLLECTOR_URL = "http://agentstack-collector:4318/v1/traces"
API_KEY = "ak_agentstack_demo_key_2026"
PROJECT_ID = "demo-simulation"

def send_agent_trace(name, steps):
    trace_id = uuid.uuid4().hex
    parent_span_id = None
    
    print(f"🚀 Starting Trace: {name} (ID: {trace_id})")
    
    base_time_us = int(time.time() * 1e6)
    current_offset_us = 0
    
    spans = []
    
    for step_name, duration_ms, status in steps:
        span_id = uuid.uuid4().hex[:16]
        start_time_us = base_time_us + current_offset_us
        end_time_us = start_time_us + (duration_ms * 1000)
        
        span = {
            "span_id": span_id,
            "trace_id": trace_id,
            "parent_span_id": parent_span_id,
            "name": step_name,
            "start_time": start_time_us,
            "end_time": end_time_us,
            "duration_ms": duration_ms,
            "status": status,
            "service_name": "demo-agent",
            "attributes": {
                "agent.step": step_name,
                "project_id": PROJECT_ID
            }
        }
        spans.append(span)
        
        # Nested logic for this demo: first span is parent of others
        if parent_span_id is None:
            parent_span_id = span_id
            
        current_offset_us += (duration_ms * 1000) + 50000 # 50ms gap
        
    payload = {"spans": spans}
    data = json.dumps(payload).encode("utf-8")
    
    req = urllib.request.Request(COLLECTOR_URL, data=data)
    req.add_header("Content-Type", "application/json")
    req.add_header("X-API-Key", API_KEY)
    
    try:
        with urllib.request.urlopen(req) as response:
            print(f"   ✅ Sent batch of {len(spans)} spans. Status: {response.status}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

if __name__ == "__main__":
    # 1. Success Flow
    send_agent_trace("Research & Report", [
        ("Initialize Agent", 50, "OK"),
        ("Query VectorDB", 800, "OK"),
        ("Summarize Results", 1200, "OK"),
        ("Post to Slack", 200, "OK")
    ])
    
    time.sleep(1)
    
    # 2. Error Flow
    send_agent_trace("Financial Analysis", [
        ("Fetch Market Data", 400, "OK"),
        ("Compute Risk Metrics", 1500, "ERROR"),
        ("Alert Admin", 100, "OK")
    ])

    print("\n✨ Done! Refresh your Dashboard to see the new traces.")
