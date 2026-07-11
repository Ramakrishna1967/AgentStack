import React from "react";
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from "recharts";

interface TokenUsageChartProps {
    data: Record<string, string | number>[]; // { timestamp: string, prompt_tokens: number, completion_tokens: number }
}

export const TokenUsageChart: React.FC<TokenUsageChartProps> = ({ data }) => {
    if (!data || data.length === 0) {
        return (
            <div className="h-64 flex items-center justify-center text-[var(--text-tertiary)] bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-primary)]">
                No token usage data available for this period.
            </div>
        );
    }

    return (
        <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={data}>
                <defs>
                    <linearGradient id="colorPrompt" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#8884d8" stopOpacity={0.8} />
                        <stop offset="95%" stopColor="#8884d8" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorCompletion" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#82ca9d" stopOpacity={0.8} />
                        <stop offset="95%" stopColor="#82ca9d" stopOpacity={0} />
                    </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-primary)" />
                <XAxis
                    dataKey="timestamp"
                    stroke="var(--text-secondary)"
                    tickFormatter={(val: string | number) => new Date(val).toLocaleDateString()}
                />
                <YAxis stroke="var(--text-secondary)" />
                <Tooltip
                    contentStyle={{ backgroundColor: "var(--bg-primary)", borderColor: "var(--border-primary)" }}
                    itemStyle={{ color: "var(--text-primary)" }}
                />
                <Legend />
                <Area
                    type="monotone"
                    dataKey="prompt_tokens"
                    stroke="#8884d8"
                    fillOpacity={1}
                    fill="url(#colorPrompt)"
                    name="Prompt Tokens"
                />
                <Area
                    type="monotone"
                    dataKey="completion_tokens"
                    stroke="#82ca9d"
                    fillOpacity={1}
                    fill="url(#colorCompletion)"
                    name="Completion Tokens"
                />
            </AreaChart>
        </ResponsiveContainer>
    );
};
