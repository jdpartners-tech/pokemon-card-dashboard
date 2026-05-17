// frontend/src/components/CardTable.tsx
"use client";

import { useRouter } from "next/navigation";
import type { CardSummary } from "@/lib/types";
import WatchlistButton from "./WatchlistButton";

interface Props {
  cards: CardSummary[];
  activeSort?: string;
}

const hkd = (v: number | null) =>
  v == null ? "—" : `HK$${v.toLocaleString("en-HK", { maximumFractionDigits: 0 })}`;

function TrendCell({ value, bold }: { value: number | null; bold?: boolean }) {
  if (value == null) return <span className="text-gray-600">—</span>;
  const up = value > 0;
  const cls = `tabular-nums ${bold ? "font-bold text-base" : "font-medium text-sm"} ${
    up ? "text-green-400" : "text-red-400"
  }`;
  return <span className={cls}>{up ? "▲" : "▼"}{Math.abs(value).toFixed(1)}%</span>;
}

function AthCell({ value }: { value: number | null }) {
  if (value == null) return <span className="text-gray-600">—</span>;
  const color = value >= -10 ? "text-amber-400" : "text-red-400";
  return <span className={`tabular-nums text-sm font-medium ${color}`}>{value.toFixed(1)}%</span>;
}

export default function CardTable({ cards, activeSort = "" }: Props) {
  const router = useRouter();

  if (cards.length === 0) {
    return (
      <div className="text-center py-16 text-gray-500">
        No cards with an upward trend found. Run a scrape or backfill to populate data.
      </div>
    );
  }

  const cols = [
    { key: "trend_7d", label: "7d" },
    { key: "trend_30d", label: "30d" },
    { key: "trend_90d", label: "90d" },
    { key: "trend_1y", label: "1y" },
  ];

  return (
    <div className="overflow-x-auto rounded-lg border border-white/10"
         style={{ background: "rgba(15, 23, 42, 0.7)", backdropFilter: "blur(6px)" }}>
      <table className="w-full text-sm min-w-[800px]">
        <thead>
          <tr className="border-b border-white/10">
            <th className="px-3 py-2 w-8" />
            <th className="px-3 py-2 w-[72px]" />
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wide">Card</th>
            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wide whitespace-nowrap">Price (HKD)</th>
            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">vs ATH</th>
            {cols.map(({ key, label }) => (
              <th key={key}
                  className={`px-3 py-2 text-right text-xs font-medium uppercase tracking-wide whitespace-nowrap ${
                    activeSort === key ? "text-blue-400" : "text-gray-400"
                  }`}>
                {label}{activeSort === key ? " ↓" : ""}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {cards.map((card) => (
            <tr
              key={card.id}
              onClick={() => router.push(`/card/${card.id}`)}
              className="hover:bg-white/5 cursor-pointer transition-colors"
              style={{ borderLeft: `3px solid ${card.accent_color ?? "#64748b"}` }}
            >
              <td className="px-3 py-2 text-center" onClick={(e) => e.stopPropagation()}>
                <WatchlistButton cardId={card.id} inWatchlist={card.in_watchlist} />
              </td>
              <td className="px-3 py-2">
                {card.image_url ? (
                  <img src={card.image_url} alt={card.name}
                       className="w-[54px] h-[76px] object-contain rounded" />
                ) : (
                  <div className="w-[54px] h-[76px] rounded bg-white/5" />
                )}
              </td>
              <td className="px-3 py-2 min-w-[200px]">
                <div className="font-semibold text-gray-100 leading-snug">
                  {card.name}
                  {card.card_number && (
                    <span className="ml-2 text-xs font-normal text-gray-400">#{card.card_number}</span>
                  )}
                </div>
                <div className="text-sm text-gray-400 mt-0.5">{card.set_name}</div>
                <div className="flex items-center gap-2 mt-1">
                  {card.psa_population != null && (
                    <span className="text-[10px] bg-white/5 border border-white/10 rounded px-1.5 py-0.5 text-gray-400">
                      Pop: {card.psa_population.toLocaleString()}
                    </span>
                  )}
                  {card.trend_consistency > 0 && (
                    <span className="text-[10px] text-green-400">
                      {card.trend_consistency}/4 wks ↑
                    </span>
                  )}
                </div>
              </td>
              <td className="px-3 py-2 text-right tabular-nums text-gray-200 whitespace-nowrap">
                {hkd(card.pricecharting_price_hkd ?? card.snkrdunk_price_hkd)}
                <div className="text-[10px] text-gray-600">
                  {card.pricecharting_price_hkd ? "PriceCharting" : card.snkrdunk_price_hkd ? "Snkrdunk" : ""}
                </div>
              </td>
              <td className="px-3 py-2 text-right"><AthCell value={card.pct_from_ath} /></td>
              {cols.map(({ key }) => (
                <td key={key} className="px-3 py-2 text-right">
                  <TrendCell
                    value={card[key as keyof CardSummary] as number | null}
                    bold={activeSort === key}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
