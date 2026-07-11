#!/usr/bin/env python3
# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

"""
AgentStack Benchmark Script

This script simulates a highly concurrent load on the AgentStack Collector
to verify its ingestion performance and capacity claims.
"""

import asyncio
import aiohttp
import time
import json
import uuid
import psutil
import argparse
import sys
from statistics import mean

COLLECTOR_URL = "http://localhost:8000/v1/traces"
API_KEY = "ak_demo123"  # Standard demo key used in DB seeding
PAYLOAD_TEMPLATE = {
    "span_id": "",
    "trace_id": "",
    "name": "benchmark_span",
    "start_time": 0,
    "end_time": 0,
    "duration_ms": 10,
    "status": "OK",
    "service_name": "benchmark_worker",
    "attributes": {"test": "true", "mode": "load"}
}

async def send_request(session: aiohttp.ClientSession, url: str, headers: dict, payload: dict) -> tuple[int, float]:
    """Send a single request and return status code and latency."""
    start_time = time.perf_counter()
    try:
        async with session.post(url, headers=headers, json=payload) as response:
            await response.read()
            latency = time.perf_counter() - start_time
            return response.status, latency
    except Exception as e:
        return 0, time.perf_counter() - start_time

def generate_payload() -> dict:
    """Generate a unique span payload matching the collector validator schema."""
    payload = PAYLOAD_TEMPLATE.copy()
    payload["span_id"] = uuid.uuid4().hex[:16]
    payload["trace_id"] = uuid.uuid4().hex
    now_ns = time.time_ns()
    payload["start_time"] = now_ns
    payload["end_time"] = now_ns + 10_000_000 # +10ms
    return {"spans": [payload]}

async def worker(session: aiohttp.ClientSession, url: str, headers: dict, requests_per_worker: int, results: list):
    """Worker task to send requests in a loop."""
    for _ in range(requests_per_worker):
        payload = generate_payload()
        status, latency = await send_request(session, url, headers, payload)
        results.append((status, latency))

async def main():
    parser = argparse.ArgumentParser(description="AgentStack Collector Benchmark")
    parser.add_argument("--workers", type=int, default=100, help="Number of concurrent workers")
    parser.add_argument("--requests", type=int, default=10000, help="Total requests to send")
    parser.add_argument("--url", type=str, default=COLLECTOR_URL, help="Collector endpoint")
    args = parser.parse_args()

    workers = args.workers
    total_requests = args.requests
    url = args.url
    reqs_per_worker = total_requests // workers

    print(f"Starting Load Test...")
    print(f"Endpoint: {url}")
    print(f"Workers: {workers}")
    print(f"Total Requests: {total_requests}")
    print("-" * 40)

    # Initial resource snapshot
    process = psutil.Process()
    cpu_start = process.cpu_percent()
    mem_start = process.memory_info().rss / 1024 / 1024 # MB

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    results = []
    
    # Run the benchmark
    start_time = time.perf_counter()
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=workers)) as session:
        tasks = [worker(session, url, headers, reqs_per_worker, results) for _ in range(workers)]
        await asyncio.gather(*tasks)
    
    total_time = time.perf_counter() - start_time

    # Final resource snapshot
    cpu_end = process.cpu_percent()
    mem_end = process.memory_info().rss / 1024 / 1024 # MB

    # Calculate metrics
    successes = [r for r in results if r[0] == 202]
    failures = [r for r in results if r[0] != 202]
    latencies = [r[1] for r in successes] if successes else [0]

    reqs_per_sec = len(successes) / total_time
    avg_latency = mean(latencies) * 1000 # ms
    max_latency = max(latencies) * 1000 if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] * 1000 if latencies else 0

    print(f"Benchmark Complete in {total_time:.2f} seconds!")
    print("-" * 40)
    print(f"Results:")
    print(f"Successful Requests (202): {len(successes)}")
    print(f"Failed Requests: {len(failures)}")
    if failures:
        print(f"  First 5 Failure codes: {[f[0] for f in failures[:5]]}")
    print(f"Ingestion Rate: {reqs_per_sec:.2f} req/sec")
    print(f"Avg Latency: {avg_latency:.2f} ms")
    print(f"p95 Latency: {p95_latency:.2f} ms")
    print(f"Max Latency: {max_latency:.2f} ms")
    print("-" * 40)
    print(f"Resource Usage (Client-side):")
    print(f"CPU Diff: {cpu_end - cpu_start:.1f}%")
    print(f"Memory Diff: {mem_end - mem_start:.2f} MB")
    
    # Save the output to a raw file format as well for the BENCHMARKS.md artifact
    with open("benchmark_results.json", "w") as f:
        json.dump({
            "total_requests": total_requests,
            "success": len(successes),
            "failures": len(failures),
            "total_time_sec": total_time,
            "reqs_per_sec": reqs_per_sec,
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency
        }, f)

if __name__ == "__main__":
    asyncio.run(main())
