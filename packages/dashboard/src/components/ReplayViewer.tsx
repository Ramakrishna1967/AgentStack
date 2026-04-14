// Copyright 2026 AgentStack Contributors
// SPDX-License-Identifier: Apache-2.0

import React, { useState, useEffect } from "react";
import { useTraceReplay } from "../hooks/useTraces";
import type { Span } from "../lib/types";
import { formatDuration, getStatusColor } from "../lib/utils";

interface ReplayViewerProps {
    traceId: string;
}

const ReplayViewer: React.FC<ReplayViewerProps> = ({ traceId }) => {
    const { data: spans, isLoading } = useTraceReplay(traceId);

    const [currentIndex, setCurrentIndex] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);

    // Auto-advance logic
    useEffect(() => {
        let interval: ReturnType<typeof setInterval>;
        if (isPlaying && spans && currentIndex < spans.length - 1) {
            interval = setInterval(() => {
                setCurrentIndex((prev) => {
                    if (prev >= spans.length - 1) {
                        setIsPlaying(false);
                        return prev;
                    }
                    return prev + 1;
                });
            }, 1000); // 1 second per step (could make this configurable)
        } else if (isPlaying && spans && currentIndex >= spans.length - 1) {
            setIsPlaying(false); // Stop playing when at the end
        }

        return () => clearInterval(interval);
    }, [isPlaying, currentIndex, spans]);

    // Reset when trace changes
    useEffect(() => {
        setCurrentIndex(0);
        setIsPlaying(false);
    }, [traceId]);

    if (isLoading) {
        return (
            <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg p-8 text-center h-[600px] flex items-center justify-center">
                <div className="animate-pulse-glow">Loading Time Machine Data...</div>
            </div>
        );
    }

    if (!spans || spans.length === 0) {
        return (
            <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg p-8 text-center h-[600px] flex items-center justify-center">
                <div className="text-[var(--text-secondary)]">No spans found for replay.</div>
            </div>
        );
    }

    const currentSpan = spans[currentIndex];

    // Extract payloads if they exist
    const inputPayload = currentSpan.attributes["input_payload"];
    const outputPayload = currentSpan.attributes["output_payload"];

    return (
        <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg overflow-hidden flex flex-col h-[700px]">
            {/* Header Toolbar */}
            <div className="bg-[var(--bg-tertiary)] border-b border-[var(--border-primary)] p-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <h3 className="font-semibold text-lg flex items-center gap-2">
                        <span className="text-[var(--accent-blue)]">⏪</span> Time Machine
                    </h3>
                    <div className="text-sm font-mono bg-[var(--bg-primary)] px-2 py-1 rounded text-[var(--text-secondary)]">
                        Step {currentIndex + 1} / {spans.length}
                    </div>
                </div>

                {/* Playback Controls */}
                <div className="flex items-center gap-2 bg-[var(--bg-primary)] p-1 rounded-lg border border-[var(--border-primary)]">
                    <button
                        onClick={() => setCurrentIndex(0)}
                        disabled={currentIndex === 0}
                        className="p-2 rounded hover:bg-[var(--bg-hover)] disabled:opacity-50 transition-colors"
                        title="Rewind to Start"
                    >
                        ⏮️
                    </button>
                    <button
                        onClick={() => setCurrentIndex(prev => Math.max(0, prev - 1))}
                        disabled={currentIndex === 0}
                        className="p-2 rounded hover:bg-[var(--bg-hover)] disabled:opacity-50 transition-colors"
                        title="Step Back"
                    >
                        ⏪
                    </button>
                    <button
                        onClick={() => setIsPlaying(!isPlaying)}
                        className={`p-2 rounded transition-colors ${isPlaying ? 'bg-[var(--accent-blue)] text-white' : 'hover:bg-[var(--bg-hover)]'}`}
                        title={isPlaying ? "Pause" : "Play"}
                    >
                        {isPlaying ? "⏸️" : "▶️"}
                    </button>
                    <button
                        onClick={() => setCurrentIndex(prev => Math.min(spans.length - 1, prev + 1))}
                        disabled={currentIndex === spans.length - 1}
                        className="p-2 rounded hover:bg-[var(--bg-hover)] disabled:opacity-50 transition-colors"
                        title="Step Forward"
                    >
                        ⏩
                    </button>
                </div>
            </div>

            {/* Timeline Scrubber */}
            <div className="px-4 py-3 border-b border-[var(--border-primary)] bg-[var(--bg-secondary)] relative h-16">
                <div className="absolute top-1/2 w-[calc(100%-2rem)] h-1 bg-[var(--bg-tertiary)] rounded -translate-y-1/2"></div>
                <div className="absolute top-1/2 w-[calc(100%-2rem)] flex justify-between items-center -translate-y-1/2 z-10">
                    {spans.map((span: Span, idx: number) => (
                        <div
                            key={span.span_id}
                            onClick={() => setCurrentIndex(idx)}
                            className={`w-4 h-4 rounded-full cursor-pointer transition-all ${idx === currentIndex
                                ? 'bg-[var(--accent-blue)] scale-150 shadow-[0_0_10px_var(--accent-blue)]'
                                : idx < currentIndex
                                    ? 'bg-[var(--accent-blue)] opacity-50'
                                    : 'bg-[var(--border-primary)] hover:bg-[var(--text-secondary)]'
                                }`}
                            title={span.name}
                        />
                    ))}
                </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 flex flex-col p-4 overflow-hidden gap-4">

                {/* Current Action Info */}
                <div className="flex justify-between items-end">
                    <div>
                        <div className="text-[var(--text-tertiary)] text-xs uppercase tracking-wider mb-1">Current Operation</div>
                        <div className="font-mono text-xl text-[var(--text-primary)]">{currentSpan.name}</div>
                    </div>
                    <div className="text-right">
                        <div className={`text-sm ${getStatusColor(currentSpan.status)}`}>{currentSpan.status}</div>
                        <div className="text-xs text-[var(--text-secondary)] mt-1">{currentSpan.duration_ms ? formatDuration(currentSpan.duration_ms) : 'N/A'}</div>
                    </div>
                </div>

                {/* Payloads Inspector (Split View) */}
                <div className="flex-1 min-h-0 grid grid-cols-2 gap-4">
                    {/* Input Pane */}
                    <div className="border border-[var(--border-primary)] rounded-lg bg-[var(--bg-primary)] flex flex-col overflow-hidden">
                        <div className="bg-[var(--bg-tertiary)] border-b border-[var(--border-primary)] px-3 py-2 text-xs font-semibold text-[var(--text-secondary)]">
                            Input Payload
                            {currentSpan.attributes["tool.name"] && <span className="ml-2 font-mono text-[var(--accent-blue)]">[{currentSpan.attributes["tool.name"]}]</span>}
                        </div>
                        <div className="flex-1 p-3 overflow-auto font-mono text-sm whitespace-pre-wrap text-[var(--text-primary)]">
                            {inputPayload ? inputPayload : <span className="text-[var(--text-tertiary)] italic">No input payload recorded.</span>}
                        </div>
                    </div>

                    {/* Output Pane */}
                    <div className="border border-[var(--border-primary)] rounded-lg bg-[var(--bg-primary)] flex flex-col overflow-hidden">
                        <div className="bg-[var(--bg-tertiary)] border-b border-[var(--border-primary)] px-3 py-2 text-xs font-semibold text-[var(--text-secondary)]">
                            Output Payload
                            {currentSpan.attributes["llm.model"] && <span className="ml-2 font-mono text-[var(--accent-green)]">[{currentSpan.attributes["llm.model"]}]</span>}
                        </div>
                        <div className="flex-1 p-3 overflow-auto font-mono text-sm whitespace-pre-wrap text-[var(--text-primary)]">
                            {outputPayload ? outputPayload : <span className="text-[var(--text-tertiary)] italic">No output payload recorded.</span>}
                        </div>
                    </div>
                </div>

                {/* Extra Metadata Footer */}
                {currentSpan.attributes["llm.tokens.in"] && (
                    <div className="text-xs text-[var(--text-secondary)] border-t border-[var(--border-primary)] pt-3 flex gap-4">
                        <span>Tokens In: <span className="font-mono text-[var(--text-primary)]">{currentSpan.attributes["llm.tokens.in"]}</span></span>
                        <span>Tokens Out: <span className="font-mono text-[var(--text-primary)]">{currentSpan.attributes["llm.tokens.out"]}</span></span>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ReplayViewer;
