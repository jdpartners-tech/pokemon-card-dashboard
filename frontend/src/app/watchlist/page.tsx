"use client";

import useSWR from "swr";
import { fetchWatchlist } from "@/lib/api";
import CardTable from "@/components/CardTable";

export default function WatchlistPage() {
  const { data, error, isLoading } = useSWR("/api/watchlist", fetchWatchlist, {
    refreshInterval: 60_000,
  });

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-100">Watchlist</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          {data ? `${data.length} cards watched` : "Loading…"}
        </p>
      </div>

      {error && (
        <div className="rounded-lg bg-red-950 border border-red-800 px-4 py-3 text-sm text-red-300">
          Failed to load watchlist.
        </div>
      )}

      {isLoading && (
        <div className="text-center py-16 text-gray-500 animate-pulse">Loading…</div>
      )}

      {data && data.length === 0 && (
        <div className="text-center py-16 text-gray-500">
          No cards in your watchlist yet. Star a card from the{" "}
          <a href="/" className="text-blue-400 hover:underline">
            cards table
          </a>
          .
        </div>
      )}

      {data && data.length > 0 && <CardTable cards={data} />}
    </div>
  );
}
