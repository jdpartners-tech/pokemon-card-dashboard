"use client";

import { useCallback, useState } from "react";
import useSWR from "swr";
import { cardsUrl, fetchCards, type CardFilters } from "@/lib/api";
import Filters from "@/components/Filters";
import CardTable from "@/components/CardTable";

export default function HomePage() {
  const [filters, setFilters] = useState<CardFilters>({});
  const url = cardsUrl(filters);
  const { data, error, isLoading } = useSWR(url, fetchCards, { refreshInterval: 60_000 });

  const handleFilters = useCallback((f: CardFilters) => setFilters(f), []);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-100">All Cards</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {data ? `${data.length} cards` : "Loading…"} · sorted by profitability score
          </p>
        </div>
        <Filters onChange={handleFilters} />
      </div>

      {error && (
        <div className="rounded-lg bg-red-950 border border-red-800 px-4 py-3 text-sm text-red-300">
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
