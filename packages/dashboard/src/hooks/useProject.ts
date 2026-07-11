// Copyright 2026 Oxly Contributors
// SPDX-License-Identifier: Apache-2.0

/**
 * useProject hook  project CRUD operations via TanStack Query
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "../lib/api";
import type { Project } from "../lib/types";

interface ProjectCreateResponse {
    project: Project;
    api_key: string;
}

/**
 * Fetch all projects
 */
export const useProjects = () => {
    return useQuery({
        queryKey: ["projects"],
        queryFn: async () => {
            const response = await apiClient.get<Project[]>("/projects");
            return response.data;
        },
    });
};

/**
 * Create a new project
 */
export const useCreateProject = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (name: string) => {
            const response = await apiClient.post<ProjectCreateResponse>("/projects", { name });
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["projects"] });
        },
    });
};

/**
 * Delete a project
 */
export const useDeleteProject = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (projectId: string) => {
            await apiClient.delete(`/projects/${projectId}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["projects"] });
        },
    });
};
