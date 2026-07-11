// Copyright 2026 Oxly Contributors
// SPDX-License-Identifier: Apache-2.0

/**
 * Trace search and filter component
 */

import React, { useState } from "react";

interface TraceSearchProps {
    onFilter: (filters: {
        status?: string;
        startDate?: number;
        endDate?: number;
        searchQuery?: string;
    }) => void;
}

const TraceSearch: React.FC<TraceSearchProps> = ({ onFilter }) => {
    const [status, setStatus] = useState<string>("");
    const [searchQuery, setSearchQuery] = useState<string>("");

    const handleApplyFilters = () => {
        onFilter({
            status: status || undefined,
            searchQuery: searchQuery || undefined,
        });
    };

    return (
        <div className="bg-black border-[3px] border-[var(--border-primary)] rounded-none shadow-[var(--shadow-md)] p-4 mb-6 font-mono">
            <div className="flex flex-wrap gap-4">
                {/* Search Input */}
                <div className="flex-1 min-w-[200px]">
                    <input
                        type="text"
                        placeholder="&gt; SEARCH_TRACES..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full px-4 py-2 bg-black border-2 border-[var(--border-primary)] rounded-none text-[var(--text-primary)] placeholder-[var(--text-tertiary)] uppercase tracking-widest focus:outline-none focus:border-[var(--accent-green)] transition-none"
                    />
                </div>

                {/* Status Filter */}
                <div className="min-w-[150px]">
                    <select
                        value={status}
                        onChange={(e) => setStatus(e.target.value)}
                        className="w-full px-4 py-2 bg-black border-2 border-[var(--border-primary)] rounded-none text-[var(--text-primary)] uppercase tracking-widest cursor-pointer focus:outline-none focus:border-[var(--accent-green)] appearance-none transition-none"
                    >
                        <option value="" className="bg-black text-white">ALL_STATUS</option>
                        <option value="OK" className="bg-black text-[#00ff41]">OK</option>
                        <option value="ERROR" className="bg-black text-red-500">ERROR</option>
                    </select>
                </div>

                {/* Apply Button */}
                <button
                    onClick={handleApplyFilters}
                    className="btn-primary rounded-none border-2 border-[var(--border-primary)] hover:border-[var(--accent-green)] px-6 py-2 uppercase tracking-widest"
                >
                    [APPLY_FILTERS]
                </button>
            </div>
        </div>
    );
};

export default TraceSearch;
