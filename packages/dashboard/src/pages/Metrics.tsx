// Copyright 2026 AgentStack Contributors
// SPDX-License-Identifier: Apache-2.0

import React, { useState, useEffect } from "react";
import apiClient from "../lib/api";
import { useProject } from "../components/ProjectSwitcher";

interface AnalyticsData {
  total_traces: number;
  avg_latency_ms: number;
  error_rate: number;
  total_cost: number;
  p95_latency_ms: number;
  success_rate: number;
  avg_spans: number;
  total_tokens: number;
}

// ── Sparkline ─────────────────────────────────────────────────────────────────
const Sparkline: React.FC<{ up?: boolean }> = ({ up = true }) => {
  const path = up
    ? "M 0 28 C 10 24 20 26 30 18 C 40 12 50 16 60 10 C 70 5 80 8 90 3"
    : "M 0 5 C 10 10 20 7 30 15 C 40 20 50 17 60 24 C 70 28 80 24 90 28";
  return (
    <svg width="90" height="32" viewBox="0 0 90 32" style={{ display: "block" }}>
      <path d={path} fill="none" stroke="#fff" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" opacity="0.6" />
    </svg>
  );
};

// ── Bar Chart from real latency data ──────────────────────────────────────────
const BarChart: React.FC<{ bars: number[] }> = ({ bars }) => {
  const max = Math.max(...bars, 1);
  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: 120 }}>
        {bars.map((h, i) => (
          <div key={i} style={{ flex: 1, height: `${(h / max) * 100}%`, background: h > max * 0.7 ? "#451a1a" : "#2a2a2a", borderRadius: "2px 2px 0 0", minWidth: 0 }} />
        ))}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", paddingTop: 8 }}>
        <span style={{ fontSize: 11, color: "#444" }}>oldest</span>
        <span style={{ fontSize: 11, color: "#444" }}>latest</span>
      </div>
    </div>
  );
};

// ── KPI Card ─────────────────────────────────────────────────────────────────
interface MetricCardProps {
  label: string; value: string; change?: string; positive?: boolean;
}
const MetricCard: React.FC<MetricCardProps> = ({ label, value, change, positive = true }) => (
  <div style={{
    background: "#0d0d0d", border: "1px solid #1a1a1a", borderRadius: 8,
    padding: "18px 18px 14px", display: "flex", flexDirection: "column",
  }}>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
      <span style={{ fontSize: 12, color: "#666" }}>{label}</span>
      {change && (
        <span style={{ fontSize: 11, color: positive ? "#22c55e" : "#ef4444", display: "flex", alignItems: "center", gap: 3 }}>
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
            {positive
              ? <path d="M5 8V2M2 5l3-3 3 3" stroke="#22c55e" strokeWidth="1.5" strokeLinecap="round"/>
              : <path d="M5 2v6M2 5l3 3 3-3" stroke="#ef4444" strokeWidth="1.5" strokeLinecap="round"/>
            }
          </svg>
          {change}
        </span>
      )}
    </div>
    <div style={{ fontSize: 32, fontWeight: 700, color: "#fff", lineHeight: 1.15, marginBottom: 12 }}>{value}</div>
    <div style={{ marginTop: "auto" }}>
      <Sparkline up={positive} />
    </div>
  </div>
);

// ── Metrics Page ──────────────────────────────────────────────────────────────
const Metrics: React.FC = () => {
  const { currentProject } = useProject();
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [latencyBars, setLatencyBars] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!currentProject) return;
    const fetchMetrics = async () => {
      setLoading(true);
      try {
        // Fetch trace list to derive metrics
        const tracesRes = await apiClient.get("/traces", {
          params: { project_id: currentProject.id, page_size: 100 }
        });
        const items = tracesRes.data.items || [];

        const total = tracesRes.data.total || items.length;
        const latencies: number[] = items.map((t: any) => t.duration_ms as number);
        const avgLat = latencies.length > 0 ? latencies.reduce((a, b) => a + b, 0) / latencies.length : 0;
        const errors = items.filter((t: any) => t.status === "ERROR").length;
        const errRate = total > 0 ? (errors / total) * 100 : 0;
        const avgSpans = items.length > 0 ? items.reduce((a: number, t: any) => a + t.span_count, 0) / items.length : 0;

        // p95
        const sorted = [...latencies].sort((a, b) => a - b);
        const p95 = sorted[Math.floor(sorted.length * 0.95)] ?? 0;

        setData({
          total_traces: total,
          avg_latency_ms: avgLat,
          p95_latency_ms: p95,
          error_rate: errRate,
          success_rate: 100 - errRate,
          total_cost: 0,
          avg_spans: avgSpans,
          total_tokens: 0,
        });

        // Use last 24 latency values for bar chart
        setLatencyBars(latencies.slice(-24).length > 0 ? latencies.slice(-24) : [0]);
      } catch (err) {
        console.error("Failed to fetch metrics:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000);
    return () => clearInterval(interval);
  }, [currentProject]);

  const fmt = (v: number, decimals = 2) => v.toFixed(decimals);

  if (!currentProject) {
    return (
      <div style={{ padding: "28px", color: "#555", fontSize: 13 }}>
        Select a project to view metrics.
      </div>
    );
  }

  return (
    <div style={{ padding: "28px 28px" }}>
      {loading ? (
        <div style={{ color: "#444", fontSize: 13 }}>Loading metrics...</div>
      ) : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
            <MetricCard
              label="Avg Latency"
              value={data ? `${fmt(data.avg_latency_ms / 1000)}s` : "—"}
              positive={true}
            />
            <MetricCard
              label="p95 Latency"
              value={data ? `${fmt(data.p95_latency_ms / 1000)}s` : "—"}
              positive={true}
            />
            <MetricCard
              label="Total Traces"
              value={data ? data.total_traces.toString() : "0"}
              positive={true}
            />
            <MetricCard
              label="Success Rate"
              value={data ? `${fmt(data.success_rate, 1)}%` : "—"}
              positive={true}
            />
            <MetricCard
              label="Avg Spans / Trace"
              value={data ? fmt(data.avg_spans, 1) : "—"}
              positive={true}
            />
            <MetricCard
              label="Error Rate"
              value={data ? `${fmt(data.error_rate, 1)}%` : "—"}
              positive={data ? data.error_rate === 0 : true}
            />
          </div>

          <div style={{ background: "#0d0d0d", border: "1px solid #1a1a1a", borderRadius: 8, padding: "18px" }}>
            <div style={{ fontSize: 15, fontWeight: 600, color: "#fff", marginBottom: 4 }}>Request Latency Distribution</div>
            <div style={{ fontSize: 12, color: "#555", marginBottom: 20 }}>
              Latency per trace — last {latencyBars.length} traces (ms)
            </div>
            <BarChart bars={latencyBars} />
          </div>
        </>
      )}
    </div>
  );
};

export default Metrics;
