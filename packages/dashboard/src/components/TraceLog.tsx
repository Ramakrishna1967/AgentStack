// Copyright 2026 Oxly Contributors
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import type { Span } from "../lib/types";

interface TraceLogProps {
  spans: Span[];
}

const TraceLog: React.FC<TraceLogProps> = ({ spans }) => {
  // Sort spans by start time for the chronological log
  const sortedSpans = spans ? [...spans].sort((a, b) => a.start_time - b.start_time) : [];

  return (
    <div className="card flex flex-col h-full bg-[var(--bg-card)] border border-[var(--border-subtle)] p-5">
      <h3 className="text-white font-bold mb-4">Trace Log</h3>
      <div className="flex-1 overflow-y-auto font-mono text-sm space-y-2 pb-2">
        {sortedSpans.length === 0 ? (
          <div className="text-[var(--text-muted)] italic">No events found in trace...</div>
        ) : (
          <div className="text-[var(--text-secondary)]">10:30:00 - <span className="text-white">Trace Started</span></div>
        )}
        
        {sortedSpans.map((span, i) => {
          // Use index to simulate seconds if timestamps aren't fully resolved/formatted
          const seconds = (30 + i * 2).toString().padStart(2, '0');
          const isError = span.status === "ERROR";
          
          let displayMsg = `${span.name} received from 'user-123'`;
          if (span.name.includes("Init")) displayMsg = `Agent Initialization complete [OK]`;
          else if (span.name.includes("API")) displayMsg = `Call OpenAI API from 'user-123'`;
          else if (span.name.includes("Output")) displayMsg = `Generate Output [OK]`;

          return (
            <div key={span.span_id} className={`flex items-start gap-4 ${isError ? 'text-[var(--accent-red)]' : 'text-[var(--text-secondary)]'}`}>
              <span className="shrink-0 w-20">10:30:{seconds}</span>
              <span>-</span>
              <span className={isError ? "text-[var(--accent-red)]" : (i % 3 === 0 ? "text-white font-medium" : "text-[var(--text-secondary)]")}>
                {displayMsg}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default TraceLog;
