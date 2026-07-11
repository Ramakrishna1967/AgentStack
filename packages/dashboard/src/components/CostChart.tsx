import React from "react";
import {
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    BarChart,
    Bar,
} from "recharts";

interface CostChartProps {
    data: Record<string, string | number>[]; // { timestamp: string, "gpt-4": number, "total_cost": number }
}

export const CostChart: React.FC<CostChartProps> = ({ data }) => {
    if (!data || data.length === 0) {
        return (
            <div className="h-64 flex items-center justify-center text-[var(--text-muted)] bg-[var(--bg-card)] rounded-lg border border-[var(--border-subtle)]">
                No cost data available for this period.
            </div>
        );
    }

    // Determine active models from data keys
    const allKeys = new Set<string>();
    data.forEach(item => {
        Object.keys(item).forEach(k => {
            if (k !== "timestamp" && k !== "total_cost") allKeys.add(k);
        });
    });
    const models = Array.from(allKeys);

    // Colors for models
    const colors = ["#8884d8", "#82ca9d", "#ffc658", "#ff7300"];

    return (
        <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                <XAxis
                    dataKey="timestamp"
                    stroke="var(--text-secondary)"
                    tickFormatter={(val) => new Date(val).toLocaleDateString()}
                />
                <YAxis stroke="var(--text-secondary)" />
                <Tooltip
                    contentStyle={{ backgroundColor: "var(--bg-void)", borderColor: "var(--border-subtle)" }}
                />
                <Legend />
                {models.map((model, idx) => (
                    <Bar
                        key={model}
                        dataKey={model}
                        stackId="a"
                        fill={colors[idx % colors.length]}
                        name={model}
                    />
                ))}
            </BarChart>
        </ResponsiveContainer>
    );
};
