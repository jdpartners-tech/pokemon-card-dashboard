// frontend/src/app/card/[id]/page.tsx
"use client";

import { use, useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import { fetchCard } from "@/lib/api";
import WatchlistButton from "@/components/WatchlistButton";
import PriceChart from "@/components/PriceChart";
import PopChart from "@/components/PopChart";

const hkd = (v: number | null) =>
  v == null ? "—" : `HK$${v.toLocaleString("en-HK", { maximumFractionDigits: 0 })}`;

function TrendTile({ label, value, active }: { label: string; value: number | null; active?: boolean }) {
  const up = value != null && value > 0;
  const down = value != null && value < 0;
  return (
    <div className={`rounded-lg border p-3 text-center ${active ? "border-blue-500/50" : "border-white/10"}`}
         style={{ background: "rgba(15, 23, 42, 0.75)", backdropFilter: "blur(4px)" }}>
      <div className={`text-xs uppercase tracking-wide mb-1 ${active ? "text-blue-400" : "text-gray-500"}`}>{label}</div>
      <div className={`text-xl font-bold tabular-nums ${
        value == null ? "text-gray-600" : up ? "text-green-400" : down ? "text-red-400" : "text-gray-300"
      }`}>
        {value == null ? "—" : `${up ? "▲" : "▼"}${Math.abs(value).toFixed(1)}%`}
      </div>
    </div>
  );
}

export default function CardPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: card, error, isLoading } = useSWR(id, fetchCard);
  const [range, setRange] = useState<"6m" | "1y" | "all">("1y");

  if (isLoading) return <div className="text-center py-16 text-gray-500 animate-pulse">Loading…</div>;
  if (error || !card) return (
    <div className="text-center py-16 text-red-400">
      Card not found. <Link href="/" className="text-blue-400 hover:underline">Back to cards</Link>
    </div>
  );

  const now = Date.now();
  const rangeDays = range === "6m" ? 180 : range === "1y" ? 365 : Infinity;
  const filteredHistory = card.history.filter((h) => {
    const diff = (now - new Date(h.scraped_at).getTime()) / 86400000;
    return diff <= rangeDays;
  });

  return (
    <div className="space-y-5 max-w-4xl">
      <Link href="/" className="text-sm text-gray-500 hover:text-gray-300">← Back to Top 50</Link>

      {/* Header */}
      <div className="flex gap-6 items-start">
        <div className="flex-shrink-0">
          {card.image_url ? (
            <img src={card.image_url} alt={card.name} className="w-40 rounded-lg shadow-xl" />
          ) : (
            <div className="w-40 h-56 rounded-lg bg-white/5 border border-white/10" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold text-gray-100 leading-tight">{card.name}</h1>
          <p className="text-gray-400 mt-1">
            {card.card_number && <span className="mr-2">#{card.card_number}</span>}
            {card.set_name}
          </p>

          <div className="flex flex-wrap gap-2 mt-3">
            <span className="bg-green-950/50 border border-green-700/50 text-green-400 text-xs rounded px-2 py-0.5">PSA 10</span>
            {card.psa_population != null && (
              <span className="bg-white/5 border border-white/10 text-gray-400 text-xs rounded px-2 py-0.5">
                Pop: {card.psa_population.toLocaleString()}
              </span>
            )}
            {card.sales_per_day != null && (
              <span className="bg-white/5 border border-white/10 text-gray-400 text-xs rounded px-2 py-0.5">
                {card.sales_per_day.toFixed(1)} sales/day
              </span>
            )}
          </div>

          <div className="mt-3 space-y-1 text-sm">
            {card.trend_consistency > 0 && (
              <div className="text-green-400">{card.trend_consistency}/4 weeks ↑ (trend consistency)</div>
            )}
            {card.pct_from_ath != null && (
              <div className={card.pct_from_ath >= -10 ? "text-amber-400" : "text-red-400"}>
                {card.pct_from_ath.toFixed(1)}% from ATH
                {card.ath != null && (
                  <span className="text-gray-500 ml-1">
                    (ATH: {hkd(card.ath)}{card.ath_date ? ` · ${new Date(card.ath_date).toLocaleDateString("en-HK", { year: "numeric", month: "short" })}` : ""})
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="mt-4">
            <WatchlistButton cardId={card.id} inWatchlist={card.in_watchlist} />
          </div>
        </div>
      </div>

      {/* Price panels */}
      <div className="grid grid-cols-2 gap-4">
        {[
          { label: "Snkrdunk · PSA 10", value: card.snkrdunk_price_hkd, url: card.snkrdunk_url, linkLabel: "View on Snkrdunk ↗" },
          { label: "PriceCharting · PSA 10", value: card.pricecharting_price_hkd, url: card.pricecharting_url, linkLabel: "View on PriceCharting ↗" },
        ].map(({ label, value, url, linkLabel }) => (
          <div key={label} className="rounded-lg border border-white/10 p-4"
               style={{ background: "rgba(15, 23, 42, 0.75)", backdropFilter: "blur(4px)" }}>
            <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
            <div className="text-2xl font-bold text-gray-100 tabular-nums mt-1">{hkd(value)}</div>
            {url ? (
              <a href={url} target="_blank" rel="noopener noreferrer"
                 className="text-xs text-blue-400 hover:underline mt-2 inline-block">
                {linkLabel}
              </a>
            ) : (
              <div className="text-xs text-gray-600 mt-2">No link available</div>
            )}
          </div>
        ))}
      </div>

      {/* Trend tiles */}
      <div className="grid grid-cols-4 gap-3">
        <TrendTile label="7 days" value={card.trend_7d} />
        <TrendTile label="30 days" value={card.trend_30d} active />
        <TrendTile label="90 days" value={card.trend_90d} />
        <TrendTile label="1 year" value={card.trend_1y} />
      </div>

      {/* Price history chart */}
      <div className="rounded-lg border border-white/10 p-4"
           style={{ background: "rgba(15, 23, 42, 0.75)", backdropFilter: "blur(4px)" }}>
        <div className="flex items-center justify-between mb-4">
          <div className="text-xs text-gray-400 uppercase tracking-wide font-medium">PSA 10 Price History</div>
          <div className="flex gap-1">
            {(["6m", "1y", "all"] as const).map((r) => (
              <button key={r} onClick={() => setRange(r)}
                      className={`text-xs px-2 py-0.5 rounded border transition-colors ${
                        range === r ? "border-blue-500 text-blue-400" : "border-white/10 text-gray-500 hover:border-white/30"
                      }`}>
                {r}
              </button>
            ))}
          </div>
        </div>
        <PriceChart history={filteredHistory} />
      </div>

      {/* PSA pop */}
      {card.psa_population != null && <PopChart population={card.psa_population} />}
    </div>
  );
}
