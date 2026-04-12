// Copyright 2026 AgentStack Contributors
// SPDX-License-Identifier: Apache-2.0

import React from "react";

interface KPICardProps {
  title: string;
  value: string | number;
  trend: string;
  trendUp: boolean;
  subtitle?: string;
}

const KPICard: React.FC<KPICardProps> = ({ title, value, trend, trendUp, subtitle }) => {
  return (
    <div className="card flex flex-col p-5 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-lg min-h-[140px]">
      <div className="flex items-start justify-between mb-2">
        <span className="text-sm font-medium text-[var(--text-secondary)]">{title}</span>
        {subtitle && <span className="text-xs text-[var(--text-muted)]">{subtitle}</span>}
      </div>
      <div className="flex items-baseline gap-2 mb-4">
        <span className="text-3xl font-bold text-white">{value}</span>
        <span className={`text-xs font-medium ${trendUp ? "text-green-400" : "text-red-400"}`}>
          {trendUp ? "+" : ""}{trend}
        </span>
      </div>
      
      {/* Sparkline Mock */}
      <div className="mt-auto h-8 w-full flex items-end">
        <svg 
          viewBox="0 0 100 30" 
          className="w-full h-full overflow-visible" 
          preserveAspectRatio="none"
        >
          <path 
            d={trendUp 
              ? "M 0 30 L 10 25 L 20 28 L 30 15 L 40 20 L 50 10 L 60 15 L 70 5 L 80 8 L 90 2 L 100 0" 
              : "M 0 0 L 10 5 L 20 2 L 30 15 L 40 10 L 50 20 L 60 15 L 70 25 L 80 22 L 90 28 L 100 30"} 
            fill="none" 
            stroke="var(--text-secondary)" 
            strokeWidth="2" 
            strokeLinecap="round" 
            strokeLinejoin="round" 
          />
          <circle cx="100" cy={trendUp ? "0" : "30"} r="3" fill="var(--text-primary)" />
        </svg>
      </div>
    </div>
  );
};

export default KPICard;
