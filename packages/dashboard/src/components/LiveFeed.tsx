// Copyright 2026 AgentStack Contributors
// SPDX-License-Identifier: Apache-2.0

/**
 * LiveFeed component — real-time trace/span streaming display
 */

import React from "react";
import { useWebSocket } from "../hooks/useWebSocket";
import { formatDuration, formatTimestamp, getStatusColor } from "../lib/utils";

const LiveFeed: React.FC = () => {
    const { isConnected, liveSpans, clearSpans } = useWebSocket();

    return (
        <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg overflow-hidden">
            {/* Header */}
            <div className="bg-[var(--bg-tertiary)] border-b border-[var(--border-primary)] px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <h3 className="font-semibold">Live Feed</h3>
                    <div className="flex items-center gap-2">
                        <span
                            className={`w-2 h-2 rounded-full ${isConnected ? "bg-[var(--accent-green)] animate-pulse-glow" : "bg-[var(--accent-red)]"
                                }`}
                        />
                        <span className="text-xs text-[var(--text-secondary)]">
                            {isConnected ? "Connected" : "Disconnected"}
                        </span>
                    </div>
                </div>
                <button
                    onClick={clearSpans}
                    className="text-xs px-3 py-1 bg-[var(--bg-hover)] border border-[var(--border-primary)] rounded hover:bg-[var(--border-primary)] transition-colors"
                >
                    Clear
                </button>
            </div>

            {/* Feed */}
            <div className="max-h-[400px] overflow-y-auto">
                {liveSpans.length === 0 ? (
                    <div className="p-8 text-center text-[var(--text-secondary)]">
                        <p className="text-lg mb-2">Feed active</p>
                        <p className="text-sm">Waiting for incoming spans...</p>
                        <p className="text-xs text-[var(--text-tertiary)] mt-1">
                            Spans will appear here in real-time
                        </p>
                    </div>
                ) : (
                    liveSpans.map((span, idx) => (
                        <div
                            key={`${span.span_id}-${idx}`}
                            className="px-4 py-3 border-b border-[var(--border-primary)] hover:bg-[var(--bg-hover)] transition-colors animate-slide-in"
                        >
                            <div className="flex items-center justify-between mb-1">
                                <span className="text-sm font-mono text-[var(--text-primary)]">
                                    {span.name}
                                </span>
                                <span className={`text-xs font-semibold ${getStatusColor(span.status)}`}>
                                    {span.status}
                                </span>
                            </div>
                            <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                                <span className="font-mono">
                                    {span.trace_id.slice(0, 8)}.../{span.span_id.slice(0, 8)}...
                                </span>
                                <span>{formatDuration(span.duration_ms)}</span>
                            </div>
                            <div className="text-xs text-[var(--text-tertiary)] mt-1">
                                {formatTimestamp(span.start_time)}
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

export default LiveFeed;
