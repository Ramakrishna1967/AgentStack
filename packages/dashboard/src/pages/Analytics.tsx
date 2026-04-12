// Copyright 2026 AgentStack Contributors
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { useProject } from "../components/ProjectSwitcher";
import { CostChart } from "../components/CostChart";
import { TokenUsageChart } from "../components/TokenUsageChart";
import KPICard from "../components/KPICard";
import { apiClient } from "../lib/api";

export const Analytics: React.FC = () => {
    const { currentProject } = useProject();

    const { data: costAnalytics, isLoading: isCostLoading } = useQuery({
        queryKey: ["analytics", "cost", currentProject?.id],
        queryFn: async () => {
            if (!currentProject?.id) return { data: [] };
            const res = await apiClient.get("/analytics/cost", {
                params: {
                    project_id: currentProject.id,
                    interval: "day",
                },
            });
            return res.data;
        },
        enabled: !!currentProject?.id,
    });

    // Mock token data for demonstration until /analytics/tokens is finalized
    const mockTokenData = [
        { timestamp: new Date(Date.now() - 6*86400000).toISOString(), prompt_tokens: 4000, completion_tokens: 1200 },
        { timestamp: new Date(Date.now() - 5*86400000).toISOString(), prompt_tokens: 6500, completion_tokens: 3000 },
        { timestamp: new Date(Date.now() - 4*86400000).toISOString(), prompt_tokens: 3200, completion_tokens: 800 },
        { timestamp: new Date(Date.now() - 3*86400000).toISOString(), prompt_tokens: 8900, completion_tokens: 4100 },
        { timestamp: new Date(Date.now() - 2*86400000).toISOString(), prompt_tokens: 12500, completion_tokens: 5600 },
        { timestamp: new Date(Date.now() - 1*86400000).toISOString(), prompt_tokens: 11200, completion_tokens: 4900 },
        { timestamp: new Date().toISOString(), prompt_tokens: 15400, completion_tokens: 7200 },
    ];

    const totalSpend = costAnalytics?.data?.reduce((acc: number, curr: any) => acc + (curr.total_cost || 0), 0) || 0;
    const totalTokens = mockTokenData.reduce((acc, curr) => acc + curr.prompt_tokens + curr.completion_tokens, 0);

    return (
        <div className="p-8 h-full flex flex-col overflow-y-auto space-y-8 font-mono">
            {/* Header */}
            <div className="flex justify-between items-end bg-black p-6 border-[3px] border-[var(--border-primary)] shadow-[var(--shadow-lg)] relative overflow-hidden">
                <div className="relative z-10">
                    <h1 className="text-4xl font-extrabold tracking-widest mb-2 text-[var(--accent-purple)] uppercase">
                        &gt; Analytics
                    </h1>
                    <p className="text-[var(--text-tertiary)] uppercase tracking-widest">
                        Cost_and_Token_Usage_Breakdown
                    </p>
                </div>
                <div className="relative z-10 hidden sm:block">
                    <span className="px-4 py-2 border-2 border-[var(--border-primary)] bg-black text-[var(--accent-purple)] font-bold text-sm shadow-[var(--shadow-sm)] uppercase tracking-widest">
                        INTERVAL: <span className="text-white">1_DAY</span>
                    </span>
                </div>
            </div>

            {/* Metrics Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <KPICard 
                    title="[TOTAL_SPEND_7D]" 
                    value={`$${totalSpend.toFixed(2)}`} 
                    trend="12%" 
                    trendUp={true}
                />
                <KPICard 
                    title="[TOTAL_TOKENS_7D]" 
                    value={`${(totalTokens / 1000).toFixed(1)}k`} 
                    trend="5%" 
                    trendUp={true}
                />
                <KPICard 
                    title="[AVG_COST_PER_TRACE]" 
                    value={`$${(totalSpend / Math.max(1, costAnalytics?.data?.length || 1)).toFixed(4)}`} 
                    trend="2%" 
                    trendUp={false}
                />
                <KPICard 
                    title="[ACTIVE_MODELS]" 
                    value="4" 
                    trend="0%"
                    trendUp={true}
                />
            </div>

            {/* Charts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 font-mono">
                {/* Cost Chart */}
                <div className="bg-black p-6 border-2 border-[var(--border-primary)] shadow-[var(--shadow-lg)] relative overflow-hidden hover:border-[var(--accent-blue)] transition-none">
                    <h2 className="text-xl font-bold mb-6 flex items-center gap-2 uppercase tracking-widest">
                        <span className="text-[var(--text-primary)]">Cost_over_Time_USD</span>
                    </h2>
                    <div className="bg-black border-2 border-[var(--border-primary)] p-4 shadow-[var(--shadow-sm)]">
                        {isCostLoading ? (
                            <div className="h-64 flex flex-col items-center justify-center">
                                <span className="text-[var(--accent-blue)] animate-pulse uppercase font-bold tracking-widest">&gt; LOADING_COST_DATA...</span>
                            </div>
                        ) : (
                            <div className="h-64">
                                <CostChart data={costAnalytics?.data || []} />
                            </div>
                        )}
                    </div>
                </div>

                {/* Token Usage Chart */}
                <div className="bg-black p-6 border-2 border-[var(--border-primary)] shadow-[var(--shadow-lg)] relative overflow-hidden hover:border-[var(--accent-green)] transition-none">
                    <h2 className="text-xl font-bold mb-6 flex items-center gap-2 uppercase tracking-widest">
                        <span className="text-[var(--text-primary)]">Token_Usage_7D</span>
                    </h2>
                    <div className="bg-black border-2 border-[var(--border-primary)] p-4 shadow-[var(--shadow-sm)]">
                        <div className="h-64">
                            <TokenUsageChart data={mockTokenData} />
                        </div>
                    </div>
                </div>
            </div>

            {/* Model Cost Breakdown Table */}
            <div className="bg-black border-[3px] border-[var(--border-primary)] shadow-[var(--shadow-lg)] overflow-hidden">
                <div className="bg-[var(--bg-tertiary)] border-b-2 border-[var(--border-primary)] px-6 py-4">
                    <h3 className="text-lg font-bold uppercase tracking-widest text-[var(--accent-purple)]">
                        [MODEL_COST_BREAKDOWN]
                    </h3>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-black border-b border-[var(--border-primary)]">
                                <th className="px-6 py-4 text-xs font-bold text-[var(--text-tertiary)] uppercase tracking-widest">Model</th>
                                <th className="px-6 py-4 text-xs font-bold text-[var(--text-tertiary)] uppercase tracking-widest">Tokens In</th>
                                <th className="px-6 py-4 text-xs font-bold text-[var(--text-tertiary)] uppercase tracking-widest">Tokens Out</th>
                                <th className="px-6 py-4 text-xs font-bold text-[var(--text-tertiary)] uppercase tracking-widest">Estimated Cost</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-[var(--border-primary)]">
                            <tr className="hover:bg-[var(--bg-secondary)] transition-none">
                                <td className="px-6 py-4 font-mono text-sm">gpt-4o</td>
                                <td className="px-6 py-4 font-mono text-sm">45.2k</td>
                                <td className="px-6 py-4 font-mono text-sm">12.8k</td>
                                <td className="px-6 py-4 font-mono text-sm text-[var(--accent-green)]">$1.24</td>
                            </tr>
                            <tr className="hover:bg-[var(--bg-secondary)] transition-none">
                                <td className="px-6 py-4 font-mono text-sm">claude-3-5-sonnet</td>
                                <td className="px-6 py-4 font-mono text-sm">28.1k</td>
                                <td className="px-6 py-4 font-mono text-sm">8.4k</td>
                                <td className="px-6 py-4 font-mono text-sm text-[var(--accent-green)]">$0.82</td>
                            </tr>
                            <tr className="hover:bg-[var(--bg-secondary)] transition-none">
                                <td className="px-6 py-4 font-mono text-sm">gemini-1.5-flash</td>
                                <td className="px-6 py-4 font-mono text-sm">112.5k</td>
                                <td className="px-6 py-4 font-mono text-sm">34.2k</td>
                                <td className="px-6 py-4 font-mono text-sm text-[var(--accent-green)]">$0.15</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default Analytics;
