"use client";

import { useCallback, useState } from "react";
import type { CardFilters } from "@/lib/api";

interface Props {
  onChange: (filters: CardFilters) => void;
}

export default function Filters({ onChange }: Props) {
  const [search, setSearch] = useState("");
  const [set, setSet] = useState("");
  const [trendingUp, setTrendingUp] = useState(false);

  const emit = useCallback(
    (overrides: Partial<{ search: string; set: string; trendingUp: boolean }>) => {
      const s = overrides.search ?? search;
      const st = overrides.set ?? set;
      const tu = overrides.trendingUp ?? trendingUp;
      onChange({
        search: s || undefined,
        set: st || undefined,
        trending_up: tu || undefined,
      });
    },
    [search, set, trendingUp, onChange]
  );

  return (
    <div className="flex flex-wrap gap-3 items-end">
      <div className="flex flex-col gap-1">
        <label className="text-xs text-gray-400 uppercase tracking-wide">Search</label>
        <input
          type="text"
          placeholder="Card name…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); emit({ search: e.target.value }); }}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-100 w-52 focus:outline-none focus:border-gray-500"
        />
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-xs text-gray-400 uppercase tracking-wide">Set</label>
        <input
          type="text"
          placeholder="e.g. Base Set"
          value={set}
          onChange={(e) => { setSet(e.target.value); emit({ set: e.target.value }); }}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-100 w-40 focus:outline-none focus:border-gray-500"
        />
      </div>
      <button
        onClick={() => { setTrendingUp((v) => { emit({ trendingUp: !v }); return !v; }); }}
        className={`px-3 py-1.5 text-sm rounded border transition-colors ${
          trendingUp
            ? "border-green-500 text-green-400 bg-green-950"
            : "border-gray-600 text-gray-400 hover:border-gray-400"
        }`}
      >
        ▲ Trending up
      </button>
    </div>
  );
}
