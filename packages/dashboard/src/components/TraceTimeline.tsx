// Copyright 2026 Oxly Contributors
// SPDX-License-Identifier: Apache-2.0

/**
 * Waterfall chart for trace timeline visualization
 */

import React from "react";
import type { Span } from "../lib/types";
import { formatDuration, getStatusColor } from "../lib/utils";

interface TraceTimelineProps {
    spans: Span[];
    onSpanClick: (span: Span) => void;
    selectedSpanId?: string;
}

const TraceTimeline: React.FC<TraceTimelineProps> = ({ spans, onSpanClick, selectedSpanId }) => {
    if (spans.length === 0) {
        return (
            <div className="p-8 text-center text-[var(--text-secondary)]">
                No spans to display
            </div>
        );
    }

    // Calculate timeline bounds
    const minTime = Math.min(...spans.map((s) => s.start_time));
    const maxTime = Math.max(...spans.map((s) => s.end_time));
    const totalDuration = maxTime - minTime;

    // Build span tree for depth calculation
    const spanDepthMap = new Map<string, number>();
    const calculateDepth = (span: Span, depth: number = 0) => {
        spanDepthMap.set(span.span_id, depth);
        spans
            .filter((s) => s.parent_span_id === span.span_id)
            .forEach((child) => calculateDepth(child, depth + 1));
    };

    // Calculate depths starting from root spans
    spans
        .filter((s) => !s.parent_span_id)
        .forEach((rootSpan) => calculateDepth(rootSpan));

    return (
        <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg overflow-hidden">
            {/* Timeline Header */}
            <div className="bg-[var(--bg-tertiary)] border-b border-[var(--border-primary)] px-4 py-3">
                <div className="flex items-center justify-between">
                    <h3 className="font-semibold">Trace Timeline ({spans.length} spans)</h3>
                    <span className="text-sm text-[var(--text-secondary)]">
                        Total: {formatDuration(totalDuration / 1_000_000)}
                    </span>
                </div>
            </div>

            {/* Waterfall Chart */}
            <div className="overflow-x-auto">
                <div className="min-w-[800px] p-4">
                    {spans.map((span) => {
                        const depth = spanDepthMap.get(span.span_id) || 0;
                        const startPercent = ((span.start_time - minTime) / totalDuration) * 100;
                        const widthPercent = ((span.end_time - span.start_time) / totalDuration) * 100;

                        const isSelected = span.span_id === selectedSpanId;

                        return (
                            <div
                                key={span.span_id}
                                className={`mb-2 cursor-pointer transition-all ${isSelected ? "scale-[1.02]" : "hover:scale-[1.01]"
                                    }`}
                                onClick={() => onSpanClick(span)}
                            >
                                {/* Span Name + Duration */}
                                <div className="flex items-center mb-1" style={{ paddingLeft: `${depth * 24}px` }}>
                                    <span className="text-sm text-[var(--text-primary)] font-mono">
                                        {span.name}
                                    </span>
                                    <span className="ml-2 text-xs text-[var(--text-tertiary)]">
                                        {formatDuration(span.duration_ms)}
                                    </span>
                                    <span className={`ml-2 text-xs ${getStatusColor(span.status)}`}>
                                        {span.status}
                                    </span>
                                </div>

                                {/* Waterfall Bar */}
                                <div className="relative h-8 bg-[var(--bg-tertiary)] rounded">
                                    <div
                                        className={`absolute h-full rounded transition-all ${span.status === "ERROR"
                                            ? "bg-[var(--accent-red)]"
                                            : "bg-[var(--accent-blue)]"
                                            } ${isSelected ? "ring-2 ring-[var(--accent-purple)]" : ""}`}
                                        style={{
                                            left: `${startPercent}%`,
                                            width: `${Math.max(widthPercent, 0.5)}%`,
                                        }}
                                    >
                                        {/* Span ID tooltip */}
                                        <div className="absolute inset-0 flex items-center justify-center text-xs text-white font-semibold opacity-0 hover:opacity-100 transition-opacity">
                                            {span.span_id.slice(0, 8)}...
                                        </div>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default TraceTimeline;
