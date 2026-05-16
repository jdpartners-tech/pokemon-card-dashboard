"use client";

import { use } from "react";
import Link from "next/link";
import useSWR from "swr";
import { fetchCard } from "@/lib/api";
import TrendBadge from "@/components/TrendBadge";
import WatchlistButton from "@/components/WatchlistButton";
import PriceChart from "@/components/PriceChart";
import CardImage from "@/components/CardImage";

const hkd = (v: number | null) =>
  v == null ? "—" : `HK$${v.toLocaleString("en-HK", { maximumFractionDigits: 0 })}`;

export default function CardPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: card, error, isLoading } = useSWR(id, fetchCard);

  if (isLoading) {
    return <div className="text-center py-16 text-gray-500 animate-pulse">Loading…</div>;
  }

  if (error || !card) {
    return (
      <div className="text-center py-16 text-red-400">
        Card not found.{" "}
        <Link href="/" className="text-blue-400 hover:underline">
          Back to cards
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header: image + title + score */}
      <div className="flex items-start gap-6">
        <CardImage name={card.name} setName={card.set_name} cardNumber={card.card_number} />

        <div className="flex-1">
          <Link href="/" className="text-sm text-gray-500 hover:text-gray-300">
            ← All cards
          </Link>
          <h1 className="mt-1 text-2xl font-bold text-gray-100">
            {card.name}
            {card.card_number && (
              <span className="ml-2 text-base font-normal text-gray-500">#{card.card_number}</span>
            )}
          </h1>
          <p className="text-gray-400 mb-4">{card.set_name}</p>

          <div className="flex items-center gap-3">
            <WatchlistButton cardId={card.id} inWatchlist={card.in_watchlist} />
            <span
              className={`text-3xl font-bold tabular-nums ${
                card.score >= 70
                  ? "text-green-400"
                  : card.score >= 40
                  ? "text-yellow-400"
                  : "text-gray-400"
              }`}
            >
              {card.score.toFixed(1)}
            </span>
            <span className="text-xs text-gray-500 leading-tight">
              profitability
              <br />
              score
            </span>
          </div>
        </div>
      </div>

      {/* Price stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Snkrdunk", value: hkd(card.snkrdunk_price_hkd) },
          { label: "PriceCharting", value: hkd(card.pricecharting_price_hkd) },
          { label: "Arbitrage gap", value: card.arb_gap > 0 ? hkd(card.arb_gap) : "—" },
          { label: "Snapshots", value: card.history.length },
        ].map(({ label, value }) => (
          <div key={label} className="bg-gray-900 border border-gray-800 rounded-lg px-4 py-3">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
            <p className="mt-1 text-lg font-semibold text-gray-100">{value}</p>
          </div>
        ))}
      </div>

      {/* Trends */}
      <div className="grid grid-cols-2 gap-4">
        {[
          { label: "7-day trend", value: <TrendBadge value={card.trend_7d} /> },
          { label: "30-day trend", value: <TrendBadge value={card.trend_30d} /> },
        ].map(({ label, value }) => (
          <div key={label} className="bg-gray-900 border border-gray-800 rounded-lg px-4 py-3">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
            <div className="mt-1">{value}</div>
          </div>
        ))}
      </div>

      {/* Price chart */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-4">
          Price history (30d)
        </h2>
        <PriceChart history={card.history} />
      </div>
    </div>
  );
}
