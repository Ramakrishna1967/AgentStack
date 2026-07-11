// Copyright 2026 Oxly Contributors
// SPDX-License-Identifier: Apache-2.0

/**
 * Span detail inspector panel
 */

import React from "react";
import type { Span } from "../lib/types";
import { formatDuration, formatTimestamp, getStatusColor } from "../lib/utils";

interface SpanDetailProps {
    span: Span | null;
    onClose: () => void;
}

const SpanDetail: React.FC<SpanDetailProps> = ({ span, onClose }) => {
    if (!span) {
        return (
            <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg p-8 text-center">
                <p className="text-[var(--text-secondary)]">Select a span to view details</p>
            </div>
        );
    }

    return (
        <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg overflow-hidden">
            {/* Header */}
            <div className="bg-[var(--bg-tertiary)] border-b border-[var(--border-primary)] px-4 py-3 flex items-center justify-between">
                <h3 className="font-semibold">Span Details</h3>
                <button
                    onClick={onClose}
                    className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
                >
                    
                </button>
            </div>

            {/* Content */}
            <div className="p-4 space-y-6 max-h-[600px] overflow-y-auto">
                {/* Basic Info */}
                <Section title="Overview">
                    <Field label="Name" value={span.name} mono />
                    <Field label="Span ID" value={span.span_id} mono copyable />
                    <Field label="Trace ID" value={span.trace_id} mono copyable />
                    {span.parent_span_id && (
                        <Field label="Parent Span ID" value={span.parent_span_id} mono copyable />
                    )}
                    <Field
                        label="Status"
                        value={
                            <span className={getStatusColor(span.status)}>{span.status}</span>
                        }
                    />
                </Section>

                {/* Timing */}
                <Section title="Timing">
                    <Field label="Duration" value={formatDuration(span.duration_ms)} />
                    <Field label="Start Time" value={formatTimestamp(span.start_time)} />
                    <Field label="End Time" value={formatTimestamp(span.end_time)} />
                </Section>

                {/* Attributes */}
                {Object.keys(span.attributes).length > 0 && (
                    <Section title="Attributes">
                        {Object.entries(span.attributes).map(([key, value]) => (
                            <Field key={key} label={key} value={value} mono />
                        ))}
                    </Section>
                )}

                {/* Events */}
                {span.events.length > 0 && (
                    <Section title="Events">
                        {span.events.map((event, idx) => (
                            <div
                                key={idx}
                                className="bg-[var(--bg-tertiary)] border border-[var(--border-primary)] rounded p-3 mb-2"
                            >
                                <div className="font-semibold text-sm mb-1">{event.name}</div>
                                <div className="text-xs text-[var(--text-secondary)]">
                                    {formatTimestamp(event.timestamp)}
                                </div>
                                {Object.keys(event.attributes).length > 0 && (
                                    <div className="mt-2 text-xs font-mono">
                                        {JSON.stringify(event.attributes, null, 2)}
                                    </div>
                                )}
                            </div>
                        ))}
                    </Section>
                )}
            </div>
        </div>
    );
};

// Helper Components
const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
    <div>
        <h4 className="text-sm font-semibold text-[var(--text-secondary)] uppercase mb-3">
            {title}
        </h4>
        <div className="space-y-2">{children}</div>
    </div>
);

const Field: React.FC<{
    label: string;
    value: React.ReactNode;
    mono?: boolean;
    copyable?: boolean;
}> = ({ label, value, mono, copyable }) => {
    const handleCopy = () => {
        if (typeof value === "string") {
            navigator.clipboard.writeText(value);
        }
    };

    return (
        <div className="flex justify-between items-start">
            <span className="text-sm text-[var(--text-secondary)] min-w-[120px]">{label}:</span>
            <span
                className={`text-sm flex-1 text-right ${mono ? "font-mono text-[var(--accent-blue)]" : "text-[var(--text-primary)]"
                    } ${copyable ? "cursor-pointer hover:underline" : ""}`}
                onClick={copyable ? handleCopy : undefined}
                title={copyable ? "Click to copy" : undefined}
            >
                {value}
            </span>
        </div>
    );
};

export default SpanDetail;
