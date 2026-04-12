// Copyright 2026 AgentStack Contributors
// SPDX-License-Identifier: Apache-2.0

/**
 * Axios API client configured for AgentStack backend
 */

import axios from "axios";

// Use the environment variable if provided (for dev), otherwise default to local origin
// In production Docker, window.location.origin will be the gateway.
const API_BASE_URL = import.meta.env.VITE_API_URL || "";

export const apiClient = axios.create({
    baseURL: `${API_BASE_URL}/api/v1`,
    headers: {
        "Content-Type": "application/json",
    },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem("agentstack_token");
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Unauthorized - clear token and redirect to login
            localStorage.removeItem("agentstack_token");
            window.location.href = "/login";
        }
        return Promise.reject(error);
    }
);

export default apiClient;
