// frontend/src/app/my-cards/page.tsx
"use client";

import { useState } from "react";
import useSWR from "swr";
import { fetchPortfolio } from "@/lib/api";
import PortfolioTable from "@/components/PortfolioTable";
import AddCardModal from "@/components/AddCardModal";
import type { PortfolioItem } from "@/lib/types";

export type PriceSource = "snkrdunk" | "pricecharting";

const hkd = (v: number) => `HK$${v.toLocaleString("en-HK", { maximumFractionDigits: 0 })}`;

function currentPrice(item: PortfolioItem, source: PriceSource): number | null {
  return source === "snkrdunk" ? item.snkrdunk_price_hkd : item.pricecharting_price_hkd;
}

export default function MyCardsPage() {
  const { data, error, isLoading, mutate } = useSWR("portfolio", fetchPortfolio);
  const [showModal, setShowModal] = useState(false);
  const [priceSource, setPriceSource] = useState<PriceSource>("snkrdunk");

  const totalInvested = data ? data.items.reduce((s, i) => s + i.purchase_price_hkd, 0) : 0;
  const totalCurrent = data
    ? data.items.reduce((s, i) => s + (currentPrice(i, priceSource) ?? 0), 0)
    : 0;
  const totalPnl = totalCurrent - totalInvested;
  const totalPnlPct = totalInvested > 0 ? (totalPnl / totalInvested) * 100 : null;

  return (
    <div className="space-y-5">
      {data && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "Cards Owned", value: String(data.items.length) },
            { label: "Total Invested", value: hkd(totalInvested) },
            { label: "Current Value", value: hkd(totalCurrent) },
            {
              label: "Total P&L",
              value: `${totalPnl >= 0 ? "+" : ""}${hkd(totalPnl)}`,
              sub: totalPnlPct != null
                ? `${totalPnlPct >= 0 ? "+" : ""}${totalPnlPct.toFixed(1)}%`
                : undefined,
              color: totalPnl >= 0 ? "text-green-400" : "text-red-400",
            },
          ].map(({ label, value, sub, color }) => (
            <div key={label} className="rounded-lg border border-white/10 px-4 py-3"
                 style={{ background: "rgba(15, 23, 42, 0.75)", backdropFilter: "blur(4px)" }}>
              <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
              <div className={`text-xl font-bold tabular-nums mt-1 ${color ?? "text-gray-100"}`}>{value}</div>
              {sub && <div className={`text-xs tabular-nums ${color}`}>{sub}</div>}
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100">My Cards</h1>
          <p className="text-sm text-gray-500 mt-0.5">Sorted by P&L % · best performers first</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Price source toggle */}
          <div className="flex items-center rounded-lg border border-white/10 overflow-hidden text-xs"
               style={{ background: "rgba(15, 23, 42, 0.75)" }}>
            <span className="px-3 py-1.5 text-gray-500 border-r border-white/10 select-none">Price</span>
            {(["snkrdunk", "pricecharting"] as PriceSource[]).map((src) => (
              <button
                key={src}
                onClick={() => setPriceSource(src)}
                className={`px-3 py-1.5 font-medium transition-colors ${
                  priceSource === src
                    ? "bg-blue-600 text-white"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                {src === "snkrdunk" ? "SNKRDunk" : "PriceCharting"}
              </button>
            ))}
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg px-4 py-2 transition-colors"
          >
            + Add Card
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-red-950/60 border border-red-800/60 px-4 py-3 text-sm text-red-300 backdrop-blur">
          Failed to load portfolio — is the backend running?
        </div>
      )}
      {isLoading && <div className="text-center py-16 text-gray-500 animate-pulse">Loading…</div>}
      {data && data.items.length === 0 && (
        <div className="text-center py-16 text-gray-500">
          No cards yet. Click &ldquo;+ Add Card&rdquo; to track your first purchase.
        </div>
      )}
      {data && data.items.length > 0 && (
        <PortfolioTable items={data.items} priceSource={priceSource} onDelete={() => mutate()} />
      )}

      {showModal && (
        <AddCardModal onClose={() => setShowModal(false)} onAdded={() => mutate()} />
      )}
    </div>
  );
}
