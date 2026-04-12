// Copyright 2026 AgentStack Contributors
// SPDX-License-Identifier: Apache-2.0

import React, { useState, useEffect } from "react";
import apiClient from "../lib/api";
import { useProject } from "../components/ProjectSwitcher";
import type { Span } from "../lib/types";

// ── Types ──────────────────────────────────────────────────────────────────────
interface RealTrace {
  trace_id: string;
  project_id: string;
  name: string;
  status: string;
  duration_ms: number;
  span_count: number;
  start_time: number; // Unix nano
  end_time: number;
}

// ── Status Icon ────────────────────────────────────────────────────────────────
const StatusIcon: React.FC<{ status: string }> = ({ status }) => {
  const isErr = status === "ERROR";
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke={isErr ? "#ef4444" : "#22c55e"} strokeWidth="1.5"/>
      {isErr ? (
        <path d="M9 9l6 6M15 9l-6 6" stroke="#ef4444" strokeWidth="1.8" strokeLinecap="round"/>
      ) : (
        <path d="M8 12l3 3 5-5" stroke="#22c55e" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      )}
    </svg>
  );
};

// ── Gantt Bar Chart ─────────────────────────────────────────────────────────
const GanttChart: React.FC<{ spans: Span[] }> = ({ spans }) => {
  if (spans.length === 0) return null;
  const minTime = Math.min(...spans.map(s => s.start_time));
  const maxTime = Math.max(...spans.map(s => s.end_time));
  const totalDuration = maxTime - minTime || 1;

  // compute depths
  const depthMap = new Map<string, number>();
  const calcDepth = (span: Span, d = 0) => {
    depthMap.set(span.span_id, d);
    spans.filter(s => s.parent_span_id === span.span_id).forEach(c => calcDepth(c, d + 1));
  };
  spans.filter(s => !s.parent_span_id).forEach(s => calcDepth(s));

  return (
    <div style={{ width: "100%", overflowX: "auto" }}>
      {/* Rows */}
      {spans.map(span => {
        const depth = depthMap.get(span.span_id) || 0;
        const left = ((span.start_time - minTime) / totalDuration) * 100;
        const width = Math.max(((span.end_time - span.start_time) / totalDuration) * 100, 1.5);
        return (
          <div key={span.span_id} style={{ display: "flex", alignItems: "center", height: 32, marginBottom: 2 }}>
            {/* Name */}
            <div style={{ width: 180, minWidth: 180, paddingLeft: 8 + depth * 16, fontSize: 12, color: "#ccc", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {depth > 0 && <span style={{ color: "#444", marginRight: 4 }}>{'└'}</span>}
              {span.name}
            </div>
            {/* Bar area */}
            <div style={{ flex: 1, position: "relative", height: "100%", display: "flex", alignItems: "center" }}>
              <div style={{ position: "relative", width: "100%", height: 18, background: "transparent" }}>
                <div style={{
                  position: "absolute", left: `${left}%`, width: `${width}%`,
                  height: "100%", background: span.status === "ERROR" ? "#451a1a" : "#1a1a1a", 
                  border: `1px solid ${span.status === "ERROR" ? "#7f1d1d" : "#333"}`,
                  borderRadius: 3, display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 10, color: "#aaa", whiteSpace: "nowrap", overflow: "hidden", paddingInline: 4,
                }}>
                </div>
              </div>
            </div>
            {/* Duration label */}
            <div style={{ width: 100, minWidth: 100, textAlign: "right", fontSize: 11, color: "#555", paddingRight: 4 }}>
              {span.duration_ms.toFixed(1)}ms
            </div>
          </div>
        );
      })}
    </div>
  );
};

// ── KPI Card ──────────────────────────────────────────────────────────────────
const KPICard: React.FC<{ label: string; value: string; sub: string }> = ({ label, value, sub }) => (
  <div style={{ background: "#0d0d0d", border: "1px solid #1a1a1a", borderRadius: 8, padding: "16px", flex: "1" }}>
    <div style={{ fontSize: 11, color: "#555", textTransform: "uppercase", marginBottom: 2 }}>{label}</div>
    <div style={{ fontSize: 24, fontWeight: 700, color: "#fff" }}>{value}</div>
    <div style={{ fontSize: 11, color: "#333" }}>{sub}</div>
  </div>
);

// ── Trace Analysis detail ──────────────────────────────────────────────────────
const TraceDetail: React.FC<{ trace: RealTrace; onBack: () => void }> = ({ trace, onBack }) => {
  const [spans, setSpans] = useState<Span[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSpans = async () => {
      try {
        const res = await apiClient.get(`/traces/${trace.trace_id}`);
        setSpans(res.data.spans || []);
      } catch (err) {
        console.error("Failed to fetch spans:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchSpans();
  }, [trace.trace_id]);

  return (
    <div style={{ padding: "28px 28px", height: "100%" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
           <button onClick={onBack} style={{ background: "transparent", border: "1px solid #333", color: "#888", borderRadius: 4, padding: "4px 8px", cursor: "pointer" }}>←</button>
           <div style={{ fontSize: 20, fontWeight: 600 }}>Trace Analysis</div>
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 15, color: "#999" }}>ID: <span style={{ color: "#fff", fontFamily: "monospace" }}>{trace.trace_id}</span></div>
        <div style={{ fontSize: 12, color: "#555" }}>{new Date(trace.start_time / 1e6).toLocaleString()}</div>
      </div>

      <div style={{ display: "flex", gap: 16, marginBottom: 16 }}>
          <KPICard label="Duration" value={`${(trace.duration_ms / 1000).toFixed(2)}s`} sub="end-to-end" />
          <KPICard label="Spans" value={trace.span_count.toString()} sub="total count" />
          <KPICard label="Status" value={trace.status} sub="final state" />
      </div>

      <div style={{ background: "#0d0d0d", border: "1px solid #1a1a1a", borderRadius: 8, padding: "16px" }}>
        {loading ? <div style={{ padding: 20, color: "#444" }}>Loading spans...</div> : <GanttChart spans={spans} />}
      </div>
    </div>
  );
};

// ── Traces List ───────────────────────────────────────────────────────────────
const TraceView: React.FC = () => {
  const { currentProject } = useProject();
  const [traces, setTraces] = useState<RealTrace[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<RealTrace | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!currentProject) return;
    const fetchTraces = async () => {
      try {
        const res = await apiClient.get("/traces", { params: { project_id: currentProject.id } });
        setTraces(res.data.items || []);
      } catch (err) {
        console.error("Failed to fetch traces:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchTraces();
  }, [currentProject]);

  if (selectedTrace) return <TraceDetail trace={selectedTrace} onBack={() => setSelectedTrace(null)} />;

  return (
    <div style={{ padding: "28px 28px", minHeight: "100%" }}>
      <div style={{ marginBottom: 20, fontSize: 13, color: "#555" }}>
        {currentProject ? `Project: ${currentProject.name}` : "Select a project to view traces"}
      </div>

      <div style={{ background: "#0a0a0a", border: "1px solid #1a1a1a", borderRadius: 8, overflow: "hidden" }}>
        {/* Head */}
        <div style={{ display: "grid", gridTemplateColumns: "44px 130px 1fr 100px 80px 1fr 30px", padding: "10px 16px", borderBottom: "1px solid #1a1a1a", background: "#0d0d0d" }}>
          {["STATUS", "TRACE ID", "NAME", "DURATION", "SPANS", "TIMESTAMP", ""].map(col => (
            <div key={col} style={{ fontSize: 11, color: "#444", fontWeight: 500, letterSpacing: "0.06em" }}>{col}</div>
          ))}
        </div>

        {/* Rows */}
        {loading ? (
             <div style={{ padding: 40, textAlign: "center", color: "#444" }}>Loading...</div>
        ) : traces.length === 0 ? (
             <div style={{ padding: 40, textAlign: "center", color: "#444" }}>No data found.</div>
        ) : traces.map((trace, i) => (
          <div
            key={trace.trace_id}
            onClick={() => setSelectedTrace(trace)}
            style={{
              display: "grid", gridTemplateColumns: "44px 130px 1fr 100px 80px 1fr 30px",
              padding: "13px 16px",
              borderBottom: i < traces.length - 1 ? "1px solid #111" : "none",
              cursor: "pointer", alignItems: "center",
              transition: "background 0.1s",
            }}
            onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = "#0d0d0d"}
            onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = "transparent"}
          >
            <div style={{ display: "flex", alignItems: "center" }}><StatusIcon status={trace.status} /></div>
            <div style={{ fontSize: 13, fontFamily: "monospace", color: "#ccc" }}>{trace.trace_id.slice(0, 8)}</div>
            <div style={{ fontSize: 13, color: "#ccc" }}>{trace.name || "Agent Run"}</div>
            <div style={{ fontSize: 13, color: "#aaa" }}>{(trace.duration_ms / 1000).toFixed(2)}s</div>
            <div style={{ fontSize: 13, color: "#aaa" }}>{trace.span_count}</div>
            <div style={{ fontSize: 12, color: "#555" }}>{new Date(trace.start_time / 1e6).toLocaleString()}</div>
            <div style={{ color: "#444", textAlign: "right" }}>›</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TraceView;
