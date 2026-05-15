"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { CardSummary } from "@/lib/types";
import TrendBadge from "./TrendBadge";
import WatchlistButton from "./WatchlistButton";

type SortKey = "score" | "trend_7d" | "trend_30d" | "arb_gap" | "snkrdunk_price_hkd" | "pricecharting_price_hkd";

interface Props {
  cards: CardSummary[];
}

const hkd = (v: number | null) =>
  v == null ? "—" : `HK$${v.toLocaleString("en-HK", { maximumFractionDigits: 0 })}`;

export default function CardTable({ cards: initialCards }: Props) {
  const router = useRouter();
  const [cards, setCards] = useState(initialCards);
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [asc, setAsc] = useState(false);

  function sort(key: SortKey) {
    if (key === sortKey) {
      setAsc((a) => !a);
    } else {
      setSortKey(key);
      setAsc(false);
    }
  }

  const sorted = [...cards].sort((a, b) => {
    const av = a[sortKey] ?? -Infinity;
    const bv = b[sortKey] ?? -Infinity;
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
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wide w-6" />
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wide">Card</th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wide">Set</th>
            <Th label="Snkrdunk" k="snkrdunk_price_hkd" />
            <Th label="PriceCharting" k="pricecharting_price_hkd" />
            <Th label="7d %" k="trend_7d" />
            <Th label="30d %" k="trend_30d" />
            <Th label="Arb gap" k="arb_gap" />
            <Th label="Score" k="score" />
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800">
          {sorted.map((card) => (
            <tr
              key={card.id}
              onClick={() => router.push(`/card/${card.id}`)}
              className="hover:bg-gray-800/60 cursor-pointer transition-colors"
            >
              <td className="px-3 py-2.5 text-center">
                <WatchlistButton
                  cardId={card.id}
                  inWatchlist={card.in_watchlist}
                  onToggle={(nowIn) => handleToggle(card.id, nowIn)}
                />
              </td>
              <td className="px-3 py-2.5 font-medium text-gray-100 whitespace-nowrap">
                {card.name}
                {card.card_number && (
                  <span className="ml-1.5 text-xs text-gray-500">#{card.card_number}</span>
                )}
              </td>
              <td className="px-3 py-2.5 text-gray-400 whitespace-nowrap">{card.set_name}</td>
              <td className="px-3 py-2.5 text-right text-gray-200 tabular-nums whitespace-nowrap">
                {hkd(card.snkrdunk_price_hkd)}
              </td>
              <td className="px-3 py-2.5 text-right text-gray-200 tabular-nums whitespace-nowrap">
                {hkd(card.pricecharting_price_hkd)}
              </td>
              <td className="px-3 py-2.5 text-right">
                <TrendBadge value={card.trend_7d} />
              </td>
              <td className="px-3 py-2.5 text-right">
                <TrendBadge value={card.trend_30d} />
              </td>
              <td className="px-3 py-2.5 text-right text-gray-300 tabular-nums">
                {card.arb_gap > 0 ? hkd(card.arb_gap) : "—"}
              </td>
              <td className="px-3 py-2.5 text-right">
                <span
                  className={`inline-block font-bold tabular-nums ${
                    card.score >= 70
                      ? "text-green-400"
                      : card.score >= 40
                      ? "text-yellow-400"
                      : "text-gray-400"
                  }`}
                >
                  {card.score.toFixed(1)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
