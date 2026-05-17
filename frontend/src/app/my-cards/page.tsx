// frontend/src/app/my-cards/page.tsx
"use client";

import { useState } from "react";
import useSWR from "swr";
import { fetchPortfolio } from "@/lib/api";
import PortfolioTable from "@/components/PortfolioTable";
import AddCardModal from "@/components/AddCardModal";

const hkd = (v: number) => `HK$${v.toLocaleString("en-HK", { maximumFractionDigits: 0 })}`;

export default function MyCardsPage() {
  const { data, error, isLoading, mutate } = useSWR("portfolio", fetchPortfolio);
  const [showModal, setShowModal] = useState(false);

  return (
    <div className="space-y-5">
      {data && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "Cards Owned", value: String(data.items.length) },
            { label: "Total Invested", value: hkd(data.total_invested) },
            { label: "Current Value", value: hkd(data.total_current_value) },
            {
              label: "Total P&L",
              value: `${data.total_pnl_hkd >= 0 ? "+" : ""}${hkd(data.total_pnl_hkd)}`,
              sub: data.total_pnl_pct != null
                ? `${data.total_pnl_pct >= 0 ? "+" : ""}${data.total_pnl_pct.toFixed(1)}%`
                : undefined,
              color: data.total_pnl_hkd >= 0 ? "text-green-400" : "text-red-400",
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
        <button
          onClick={() => setShowModal(true)}
          className="bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg px-4 py-2 transition-colors"
        >
          + Add Card
        </button>
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
        <PortfolioTable items={data.items} onDelete={() => mutate()} />
      )}

      {showModal && (
        <AddCardModal onClose={() => setShowModal(false)} onAdded={() => mutate()} />
      )}
    </div>
  );
}
