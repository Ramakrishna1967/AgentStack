// Copyright 2026 AgentStack Contributors
// SPDX-License-Identifier: Apache-2.0


/**
 * WebSocket manager hook for real-time trace streaming
 */

import { useEffect, useRef, useState, useCallback } from "react";
import type { Span } from "../lib/types";

// Same-origin default, mirroring lib/api.ts — the merged app serves the
// dashboard and the API from the same port, so there's no separate gateway host.
const WS_URL =
    import.meta.env.VITE_WS_URL ||
    `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws/traces`;

export interface WSMessage<T = unknown> {
    type: "span" | "trace" | "ping" | "pong" | "filter_ack" | "error" | "alert";
    data?: T;
}

// Configuration
const MAX_ITEMS = 100;
const MAX_RECONNECT_DELAY = 30000; // 30 seconds
const BASE_RECONNECT_DELAY = 1000; // 1 second

export interface SecurityAlert {
    id: string;
    rule: string;
    severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
    description: string;
    created_at: number;
    project_id?: string;
    trace_id?: string;
    score?: number;
    evidence?: string;
}

export const useWebSocket = (projectId?: string) => {
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
    const reconnectAttempts = useRef(0);
    const [isConnected, setIsConnected] = useState(false);
    const [liveSpans, setLiveSpans] = useState<Span[]>([]);
    const [liveAlerts, setLiveAlerts] = useState<SecurityAlert[]>([]);



    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        console.log(`[WS] Connecting... (Attempt ${reconnectAttempts.current + 1})`);
        const ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            setIsConnected(true);
            reconnectAttempts.current = 0; // Reset attempts on success
            console.log("[WS] Connected to trace feed");

            // Send filter if project selected
            if (projectId) {
                ws.send(JSON.stringify({ type: "filter", project_id: projectId }));
            }
        };

        ws.onmessage = (event) => {
            try {
                const message: WSMessage = JSON.parse(event.data);

                if (message.type === "pong") return;

                if (message.type === "ping") {
                    ws.send(JSON.stringify({ type: "pong" }));
                    return;
                }

                if (message.type === "span" && message.data) {
                    const span = message.data as Span;
                    if (projectId && span.project_id !== projectId) return;

                    setLiveSpans((prev) => {
                        const updated = [span, ...prev];
                        return updated.slice(0, MAX_ITEMS);
                    });
                }

                if (message.type === "alert" && message.data) {
                    const alert = message.data as SecurityAlert;
                    if (projectId && alert.project_id && alert.project_id !== projectId) return;

                    setLiveAlerts((prev) => {
                        const updated = [alert, ...prev];
                        return updated.slice(0, MAX_ITEMS);
                    });
                }
            } catch (err) {
                console.error("[WS] Parse error:", err);
            }
        };

        ws.onclose = () => {
            setIsConnected(false);
            wsRef.current = null;

            // Calculate exponential backoff
            const delay = Math.min(
                BASE_RECONNECT_DELAY * Math.pow(2, reconnectAttempts.current),
                MAX_RECONNECT_DELAY
            );

            console.log(`[WS] Disconnected. Reconnecting in ${delay}ms...`);
            reconnectTimer.current = setTimeout(() => {
                reconnectAttempts.current++;
                // eslint-disable-next-line react-hooks/immutability
                connect();
            }, delay);
        };

        ws.onerror = (err) => {
            console.error("[WS] Error:", err);
            ws.close();
        };

        wsRef.current = ws;
    }, [projectId]);

    const disconnect = useCallback(() => {
        if (reconnectTimer.current) {
            clearTimeout(reconnectTimer.current);
            reconnectTimer.current = undefined;
        }
        wsRef.current?.close();
        wsRef.current = null;
        setIsConnected(false);
        reconnectAttempts.current = 0;
    }, []);

    const sendFilter = useCallback((filters: Record<string, string>) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: "filter", ...filters }));
        }
    }, []);

    const clearSpans = useCallback(() => {
        setLiveSpans([]);
    }, []);

    const clearAlerts = useCallback(() => {
        setLiveAlerts([]);
    }, []);

    useEffect(() => {
        connect();
        return () => disconnect();
    }, [connect, disconnect]);

    return { isConnected, liveSpans, liveAlerts, sendFilter, clearSpans, clearAlerts };
};
