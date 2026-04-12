// Copyright 2026 AgentStack Contributors
// SPDX-License-Identifier: Apache-2.0

/**
 * TanStack Query hooks for fetching trace data
 */

import { useQuery } from "@tanstack/react-query";
import apiClient from "../lib/api";
import type { Span, Trace, TraceDetail, PaginatedResponse } from "../lib/types";

export interface TraceFilters {
    project_id?: string;
    status?: string | null;
    start_date?: number;
    end_date?: number;
    page?: number;
    page_size?: number;
    search?: string;
}

/**
 * Fetch paginated list of traces with filters
 */
export const useTraces = (filters: TraceFilters = {}) => {
    return useQuery({
        queryKey: ["traces", filters],
        queryFn: async () => {
            const params = new URLSearchParams();
            Object.entries(filters).forEach(([key, value]) => {
                if (value !== undefined && value !== null) {
                    params.append(key, String(value));
                }
            });
            const response = await apiClient.get<PaginatedResponse<Trace>>(
                `/traces?${params.toString()}`
            );
            return response.data;
        },
    });
};

/**
 * Fetch single trace with full span tree
 */
export const useTraceDetail = (traceId: string | null) => {
    return useQuery({
        queryKey: ["trace", traceId],
        queryFn: async () => {
            if (!traceId) return null;
            const response = await apiClient.get<TraceDetail>(`/traces/${traceId}`);
            return response.data;
        },
        enabled: !!traceId,
    });
};

/**
 * Fetch dashboard metrics (simplified aggregation)
 */
export const useDashboardMetrics = (projectId?: string) => {
    return useQuery({
        queryKey: ["metrics", projectId],
        queryFn: async () => {
            // For MVP, fetch recent traces and calculate metrics client-side
            const params = projectId ? `?project_id=${projectId}&page_size=100` : "?page_size=100";
            const response = await apiClient.get<PaginatedResponse<Trace>>(`/traces${params}`);
            const traces: Trace[] = response.data.items;

            const totalTraces = traces.length;
            const errorCount = traces.filter((t) => t.status === "ERROR").length;
            const errorRate = totalTraces > 0 ? (errorCount / totalTraces) * 100 : 0;
            const avgLatency =
                traces.reduce((sum, t) => sum + (t.duration_ms || 0), 0) / (totalTraces || 1);
            const totalCost = totalTraces * 0.001; // Placeholder cost estimation

            const latencyData = traces.slice(0, 50).reverse().map((t) => ({
                name: `Trace ${t.trace_id.substring(0, 4)}`,
                latency: t.duration_ms || 0,
                category: t.status === "ERROR" ? "error" : "trace"
            }));

            return {
                totalTraces,
                errorRate: errorRate.toFixed(1),
                avgLatency: Math.round(avgLatency),
                totalCost: totalCost.toFixed(2),
                latencyData: latencyData
            };
        },
    });
};

/**
 * Fetch trace spans ordered by time for Time Machine replay
 */
export const useTraceReplay = (traceId: string | null) => {
    return useQuery({
        queryKey: ["trace_replay", traceId],
        queryFn: async () => {
            if (!traceId) return null;
            const response = await apiClient.get<Span[]>(`/traces/${traceId}/replay`);
            return response.data;
        },
        enabled: !!traceId,
    });
};
