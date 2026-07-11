// Copyright 2026 Oxly Contributors
// SPDX-License-Identifier: Apache-2.0

/**
 * Utility functions for formatting and display
 */

/**
 * Format duration in milliseconds to human-readable string
 */
export function formatDuration(ms: number): string {
    if (ms < 1000) {
        return `${ms}ms`;
    } else if (ms < 60000) {
        return `${(ms / 1000).toFixed(2)}s`;
    } else {
        const minutes = Math.floor(ms / 60000);
        const seconds = ((ms % 60000) / 1000).toFixed(0);
        return `${minutes}m ${seconds}s`;
    }
}

/**
 * Format timestamp (nanoseconds) to date string
 */
export function formatTimestamp(ns: number): string {
    const date = new Date(ns / 1_000_000); // Convert ns to ms
    return date.toLocaleString();
}

/**
 * Format relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(ns: number): string {
    const now = Date.now();
    const ms = ns / 1_000_000;
    const diffMs = now - ms;
    const diffSeconds = Math.floor(diffMs / 1000);
    const diffMinutes = Math.floor(diffSeconds / 60);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSeconds < 60) {
        return `${diffSeconds}s ago`;
    } else if (diffMinutes < 60) {
        return `${diffMinutes}m ago`;
    } else if (diffHours < 24) {
        return `${diffHours}h ago`;
    } else {
        return `${diffDays}d ago`;
    }
}

/**
 * Truncate long strings with ellipsis
 */
export function truncate(str: string, maxLength: number = 50): string {
    if (str.length <= maxLength) return str;
    return str.slice(0, maxLength) + "...";
}

/**
 * Get status color class
 */
export function getStatusColor(status: string): string {
    switch (status) {
        case "OK":
            return "text-green-500";
        case "ERROR":
            return "text-red-500";
        default:
            return "text-gray-500";
    }
}

/**
 * Get severity color class
 */
export function getSeverityColor(severity: string): string {
    switch (severity) {
        case "critical":
            return "text-red-600";
        case "high":
            return "text-orange-500";
        case "medium":
            return "text-yellow-500";
        case "low":
            return "text-blue-500";
        default:
            return "text-gray-500";
    }
}
