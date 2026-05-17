// frontend/src/components/AddCardModal.tsx
"use client";

import { useState } from "react";
import useSWR from "swr";
import { cardsUrl, fetchCards, addPortfolioItem } from "@/lib/api";

interface Props {
  onClose: () => void;
  onAdded: () => void;
}

export default function AddCardModal({ onClose, onAdded }: Props) {
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedName, setSelectedName] = useState("");
  const [price, setPrice] = useState("");
  const [purchasedAt, setPurchasedAt] = useState(new Date().toISOString().split("T")[0]);
  const [saving, setSaving] = useState(false);

  const { data: results } = useSWR(
    search.length >= 2 ? cardsUrl({ search, limit: 10 }) : null,
    fetchCards
  );

  async function handleAdd() {
    if (!selectedId || !price || !purchasedAt) return;
    setSaving(true);
    await addPortfolioItem({
      card_id: selectedId,
      purchase_price_hkd: parseFloat(price),
      purchased_at: purchasedAt,
    });
    setSaving(false);
    onAdded();
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
         style={{ background: "rgba(0,0,0,0.7)" }} onClick={onClose}>
      <div className="w-full max-w-md rounded-xl border border-white/10 p-6 space-y-4"
           style={{ background: "rgba(15, 23, 42, 0.95)", backdropFilter: "blur(12px)" }}
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h2 className="font-bold text-gray-100">Add Card to Portfolio</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300">✕</button>
        </div>

        <div className="space-y-1">
          <label className="text-xs text-gray-400">Search card</label>
          <input
            type="text" value={search} placeholder="Type card name…"
            onChange={(e) => { setSearch(e.target.value); setSelectedId(null); setSelectedName(""); }}
            className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-white/30"
          />
          {results && results.length > 0 && !selectedId && (
            <div className="border border-white/10 rounded-lg overflow-hidden max-h-48 overflow-y-auto">
              {results.map((c) => (
                <button key={c.id}
                        onClick={() => { setSelectedId(c.id); setSelectedName(c.name); setSearch(c.name); }}
                        className="w-full text-left px-3 py-2 text-sm text-gray-200 hover:bg-white/5 border-b border-white/5 last:border-0">
                  <div className="font-medium">{c.name}</div>
                  <div className="text-xs text-gray-500">{c.set_name}</div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs text-gray-400">Purchase price (HKD)</label>
            <input type="number" value={price} onChange={(e) => setPrice(e.target.value)}
                   placeholder="e.g. 18000"
                   className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-white/30" />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-gray-400">Purchase date</label>
            <input type="date" value={purchasedAt} onChange={(e) => setPurchasedAt(e.target.value)}
                   className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-white/30" />
          </div>
        </div>

        <button
          onClick={handleAdd}
          disabled={!selectedId || !price || saving}
          className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg py-2 text-sm font-medium transition-colors"
        >
          {saving ? "Adding…" : "Add to My Cards"}
        </button>
      </div>
    </div>
  );
}
