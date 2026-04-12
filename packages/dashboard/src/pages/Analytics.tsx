// Copyright 2026 AgentStack Contributors
// SPDX-License-Identifier: Apache-2.0

import React, { useState, useEffect } from "react";
import apiClient from "../lib/api";
import { useProject } from "../components/ProjectSwitcher";

const S = {
  card: { background: "#0d0d0d", border: "1px solid #1e1e1e", borderRadius: 8 } as React.CSSProperties,
  label: { fontSize: 11, color: "#555", letterSpacing: "0.06em", textTransform: "uppercase" as const, fontWeight: 500 },
};

const KPI: React.FC<{ label: string; value: string; sub?: string }> = ({ label, value, sub }) => (
  <div style={{ ...S.card, padding: "18px 18px 14px", display: "flex", flexDirection: "column", gap: 4 }}>
    <div style={S.label}>{label}</div>
    <div style={{ fontSize: 34, fontWeight: 700, color: "#fff", lineHeight: 1.1 }}>{value}</div>
    {sub && <div style={{ fontSize: 11, color: "#333", marginTop: 4 }}>{sub}</div>}
  </div>
);

const BarChart: React.FC<{ data: any[] }> = ({ data }) => {
  const max = Math.max(...data.map(d => d.total_cost), 0.001);
            <span style={{ fontSize: 13, color: "#fff", fontWeight: 600 }}>${meta.cost.toFixed(4)}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
