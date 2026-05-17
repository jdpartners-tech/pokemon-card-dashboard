"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { CardSummary } from "@/lib/types";
import WatchlistButton from "./WatchlistButton";
import CardThumb from "./CardThumb";

type SortKey = "trend_7d" | "trend_30d" | "trend_90d" | "snkrdunk_price_hkd" | "pricecharting_price_hkd";

interface Props {
  cards: CardSummary[];
}

const hkd = (v: number | null) =>
  v == null ? "—" : `HK$${v.toLocaleString("en-HK", { maximumFractionDigits: 0 })}`;

function TrendCell({ value }: { value: number | null }) {
  if (value == null) return <span className="text-gray-600">—</span>;
  const up = value > 0;
  const down = value < 0;
  return (
    <span className={`tabular-nums font-medium ${up ? "text-green-400" : down ? "text-red-400" : "text-gray-400"}`}>
      {up ? "▲" : down ? "▼" : ""}{Math.abs(value).toFixed(1)}%
    </span>
  );
}

export default function CardTable({ cards: initialCards }: Props) {
  const router = useRouter();
  const [cards, setCards] = useState(initialCards);
  const [sortKey, setSortKey] = useState<SortKey>("trend_7d");
  const [asc, setAsc] = useState(false);

  function sort(key: SortKey) {
    if (key === sortKey) setAsc((a) => !a);
    else { setSortKey(key); setAsc(false); }
  }

  const sorted = [...cards].sort((a, b) => {
    const av = (a[sortKey] as number | null) ?? -Infinity;
    const bv = (b[sortKey] as number | null) ?? -Infinity;
    return asc ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1);
  });

  function handleToggle(cardId: string, nowIn: boolean) {
    setCards((cs) => cs.map((c) => c.id === cardId ? { ...c, in_watchlist: nowIn } : c));
  }

  function Th({ label, k }: { label: string; k: SortKey }) {
    const active = sortKey === k;
    return (
      <th
        onClick={() => sort(k)}
        className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wide cursor-pointer select-none whitespace-nowrap hover:text-gray-200"
      >
        {label} {active ? (asc ? "↑" : "↓") : ""}
      </th>
    );
  }

  if (cards.length === 0) {
    return (
      <div className="text-center py-16 text-gray-500">
        No cards found. Run a scrape to populate data.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-700">
      <table className="w-full text-sm">
        <thead className="bg-gray-800 border-b border-gray-700">
          <tr>
            <th className="px-3 py-2 w-6" />
            <th className="px-3 py-2 w-10" />
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wide">Card</th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wide">Set</th>
            <Th label="Snkrdunk" k="snkrdunk_price_hkd" />
            <Th label="PriceCharting" k="pricecharting_price_hkd" />
            <Th label="7d" k="trend_7d" />
            <Th label="1m" k="trend_30d" />
            <Th label="3m" k="trend_90d" />
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800">
          {sorted.map((card) => (
            <tr
              key={card.id}
              onClick={() => router.push(`/card/${card.id}`)}
              className="hover:bg-gray-800/60 cursor-pointer transition-colors"
            >
              <td className="px-3 py-2 text-center">
                <WatchlistButton
                  cardId={card.id}
                  inWatchlist={card.in_watchlist}
                  onToggle={(nowIn) => handleToggle(card.id, nowIn)}
                />
              </td>
              <td className="px-3 py-2">
                <CardThumb name={card.name} cardNumber={card.card_number} />
              </td>
              <td className="px-3 py-2 font-medium text-gray-100 whitespace-nowrap">
                {card.name}
                {card.card_number && (
                  <span className="ml-1.5 text-xs text-gray-500">#{card.card_number}</span>
                )}
              </td>
              <td className="px-3 py-2 text-gray-400 whitespace-nowrap">{card.set_name}</td>
              <td className="px-3 py-2 text-right text-gray-200 tabular-nums whitespace-nowrap">
                {hkd(card.snkrdunk_price_hkd)}
              </td>
              <td className="px-3 py-2 text-right text-gray-200 tabular-nums whitespace-nowrap">
                {hkd(card.pricecharting_price_hkd)}
              </td>
              <td className="px-3 py-2 text-right"><TrendCell value={card.trend_7d} /></td>
              <td className="px-3 py-2 text-right"><TrendCell value={card.trend_30d} /></td>
              <td className="px-3 py-2 text-right"><TrendCell value={card.trend_90d} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
