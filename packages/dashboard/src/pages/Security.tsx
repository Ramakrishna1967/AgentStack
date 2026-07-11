// Copyright 2026 Oxly Contributors
// SPDX-License-Identifier: Apache-2.0

import React, { useState, useEffect } from "react";
import apiClient from "../lib/api";
import { useProject } from "../components/ProjectSwitcher";

const S = {
  card: { background: "#0d0d0d", border: "1px solid #1e1e1e", borderRadius: 8 } as React.CSSProperties,
  label: { fontSize: 11, color: "#555", letterSpacing: "0.06em", textTransform: "uppercase" as const, fontWeight: 500 },
};

interface SecurityAlert {
  id: string;
  severity: string;
  rule_name: string;
  trace_id: string;
  description: string;
  created_at: string;
  project_id: string;
}

const SeverityBadge: React.FC<{ level: string }> = ({ level }) => {
  const colors: Record<string, { bg: string; text: string }> = {
    critical: { bg: "rgba(239,68,68,0.12)",   text: "#ef4444" },
    high:     { bg: "rgba(245,158,11,0.12)",   text: "#f59e0b" },
    medium:   { bg: "rgba(59,130,246,0.12)",   text: "#60a5fa" },
    low:      { bg: "rgba(34,197,94,0.12)",    text: "#22c55e" },
  };
  const c = colors[level] || colors.low;
  return (
    <span style={{ background: c.bg, color: c.text, fontSize: 10, fontWeight: 600, padding: "2px 8px", borderRadius: 4, letterSpacing: "0.04em" }}>
      {level.toUpperCase()}
    </span>
  );
};

const ThreatSummary: React.FC<{ alerts: SecurityAlert[] }> = ({ alerts }) => {
  const critical = alerts.filter(a => a.severity === "critical").length;
  const high = alerts.filter(a => a.severity === "high").length;
  let level = "Normal";
  let color = "#22c55e";
  let bg = "rgba(34,197,94,0.1)";
  if (critical > 0) { level = "Critical"; color = "#ef4444"; bg = "rgba(239,68,68,0.1)"; }
  else if (high > 0) { level = "Elevated"; color = "#f59e0b"; bg = "rgba(245,158,11,0.1)"; }

  return (
    <div style={{ ...S.card, padding: 16 }}>
      <div style={S.label}>Current Threat Level</div>
      <div style={{ fontSize: 24, fontWeight: 700, color: "#fff", marginTop: 8, marginBottom: 4 }}>{level}</div>
      <span style={{ fontSize: 11, color, background: bg, padding: "2px 8px", borderRadius: 4 }}>
        {critical > 0 ? `${critical} Critical` : high > 0 ? `${high} High Alerts` : "All Clear"}
      </span>
      <p style={{ fontSize: 12, color: "#555", marginTop: 10, lineHeight: 1.6 }}>
        {alerts.length === 0
          ? "No threats detected."
          : `${alerts.length} alert${alerts.length !== 1 ? "s" : ""} detected in the current project.`}
      </p>
    </div>
  );
};

const GUARDRAILS = [
  "Prompt Injection Filter",
  "PII Data Scrubbing",
  "Rate Limit Anomaly Engine",
  "Token Explosion Detector",
];

export const Security: React.FC = () => {
  const { currentProject } = useProject();
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!currentProject) return;
    const fetchAlerts = async () => {
      setLoading(true);
      try {
        const res = await apiClient.get("/security/alerts", {
          params: { project_id: currentProject.id, limit: 50 },
        });
        setAlerts(res.data.alerts || res.data || []);
      } catch (err) {
        console.error("Failed to fetch security alerts:", err);
        setAlerts([]);
      } finally {
        setLoading(false);
      }
    };
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 10000);
    return () => clearInterval(interval);
  }, [currentProject]);

  const formatTime = (ts: string) => {
    try { return new Date(ts).toLocaleTimeString([], { hour12: false }); }
    catch { return ts; }
  };

  return (
    <div style={{ padding: "28px", maxWidth: 1100 }}>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 20, fontWeight: 600, color: "#fff", marginBottom: 4 }}>Security Control Center</h1>
        <p style={{ fontSize: 13, color: "#555" }}>Real-time threat detection, prompt injection scanning, and PII monitoring.</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 12 }}>
        {/* Left column */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <ThreatSummary alerts={alerts} />

          {/* Guardrails */}
          <div style={{ ...S.card, overflow: "hidden" }}>
            <div style={{ padding: "12px 16px", borderBottom: "1px solid #1a1a1a" }}>
              <span style={S.label}>Active Guardrails</span>
            </div>
            {GUARDRAILS.map(g => (
              <div key={g} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 16px", borderBottom: "1px solid #111" }}>
                <span style={{ fontSize: 12, color: "#aaa" }}>{g}</span>
                <span style={{ fontSize: 10, color: "#22c55e", background: "rgba(34,197,94,0.1)", padding: "2px 8px", borderRadius: 4 }}>Active</span>
              </div>
            ))}
          </div>

          {/* Stats */}
          <div style={{ ...S.card, padding: 16 }}>
            <div style={{ ...S.label, marginBottom: 12 }}>Alert Breakdown</div>
            {["critical", "high", "medium", "low"].map(sev => {
              const count = alerts.filter(a => a.severity === sev).length;
              const colors: Record<string, string> = { critical: "#ef4444", high: "#f59e0b", medium: "#60a5fa", low: "#22c55e" };
              return (
                <div key={sev} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBlock: 6 }}>
                  <span style={{ fontSize: 12, color: "#888" }}>{sev.toUpperCase()}</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: count > 0 ? colors[sev] : "#333" }}>{count}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right column  Alert Feed */}
        <div style={{ ...S.card, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ padding: "14px 16px", borderBottom: "1px solid #1a1a1a", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: alerts.length > 0 ? "#ef4444" : "#22c55e", boxShadow: `0 0 8px ${alerts.length > 0 ? "#ef4444" : "#22c55e"}` }} />
              <span style={{ fontSize: 13, fontWeight: 600, color: "#fff" }}>Live Threat Feed</span>
            </div>
            <span style={{ fontSize: 11, color: alerts.length > 0 ? "#ef4444" : "#22c55e", background: alerts.length > 0 ? "rgba(239,68,68,0.1)" : "rgba(34,197,94,0.1)", padding: "2px 10px", borderRadius: 4 }}>
              {alerts.length} {alerts.length === 1 ? "Alert" : "Alerts"}
            </span>
          </div>
          <div style={{ flex: 1, overflowY: "auto" }}>
            {loading ? (
              <div style={{ padding: 40, textAlign: "center", color: "#444", fontSize: 13 }}>Loading alerts...</div>
            ) : alerts.length === 0 ? (
              <div style={{ padding: 40, textAlign: "center", color: "#444", fontSize: 13 }}>
                No security alerts for this project.
              </div>
            ) : alerts.map((alert, i) => (
              <div key={alert.id} style={{ padding: "14px 16px", borderBottom: i < alerts.length - 1 ? "1px solid #111" : "none" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <SeverityBadge level={alert.severity} />
                  <span style={{ fontSize: 12, fontFamily: "monospace", color: "#555" }}>{alert.rule_name}</span>
                  <span style={{ marginLeft: "auto", fontSize: 11, fontFamily: "monospace", color: "#444" }}>{formatTime(alert.created_at)}</span>
                </div>
                <div style={{ fontSize: 12, color: "#888", lineHeight: 1.6, marginBottom: 4 }}>{alert.description}</div>
                {alert.trace_id && (
                  <div style={{ fontSize: 11, fontFamily: "monospace", color: "#444" }}>
                    trace: <span style={{ color: "#666" }}>{alert.trace_id.slice(0, 8)}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
