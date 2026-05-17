// frontend/src/app/page.tsx
"use client";

import { useState } from "react";
import useSWR from "swr";
import { cardsUrl, fetchCards, type CardFilters } from "@/lib/api";
import CardTable from "@/components/CardTable";

export default function HomePage() {
  const [filters, setFilters] = useState<CardFilters>({ sort: "trend_30d" });
  const url = cardsUrl(filters);
  const { data, error, isLoading } = useSWR(url, fetchCards, { refreshInterval: 60_000 });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-100">Top Trending PSA 10 Cards</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {data ? `Top ${data.length}` : "Loading…"} · sorted by {filters.sort ?? "30d"} trend
          </p>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="text"
            placeholder="Search cards…"
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value || undefined }))}
            className="bg-white/5 border border-white/10 rounded px-3 py-1.5 text-sm text-gray-100 w-48 focus:outline-none focus:border-white/30 backdrop-blur"
          />
          <select
            value={filters.sort ?? "trend_30d"}
            onChange={(e) => setFilters((f) => ({ ...f, sort: e.target.value as CardFilters["sort"] }))}
            className="bg-white/5 border border-white/10 rounded px-3 py-1.5 text-sm text-gray-100 focus:outline-none backdrop-blur"
          >
            <option value="trend_7d">Sort: 7d</option>
            <option value="trend_30d">Sort: 30d</option>
            <option value="trend_90d">Sort: 90d</option>
            <option value="trend_1y">Sort: 1y</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-red-950/60 border border-red-800/60 px-4 py-3 text-sm text-red-300 backdrop-blur">
          Failed to load cards — is the backend running?
        </div>
      )}
      {isLoading && (
        <div className="text-center py-16 text-gray-500 animate-pulse">Loading cards…</div>
      )}
      {data && <CardTable cards={data} />}
    </div>
  );
}
