// frontend/src/components/PortfolioTable.tsx
"use client";

import { useRouter } from "next/navigation";
import type { PortfolioItem } from "@/lib/types";
import type { PriceSource } from "@/app/my-cards/page";
import { deletePortfolioItem } from "@/lib/api";

interface Props {
  items: PortfolioItem[];
  priceSource: PriceSource;
  onDelete: () => void;
}

const hkd = (v: number | null) =>
  v == null ? "—" : `HK$${v.toLocaleString("en-HK", { maximumFractionDigits: 0 })}`;

function getPrice(item: PortfolioItem, source: PriceSource): number | null {
  return source === "snkrdunk" ? item.snkrdunk_price_hkd : item.pricecharting_price_hkd;
}

export default function PortfolioTable({ items, priceSource, onDelete }: Props) {
  const router = useRouter();

  async function handleDelete(e: React.MouseEvent, id: string) {
    e.stopPropagation();
    await deletePortfolioItem(id);
    onDelete();
  }

  // Sort by P&L % descending using the selected price source
  const sorted = [...items].sort((a, b) => {
    const pa = getPrice(a, priceSource);
    const pb = getPrice(b, priceSource);
    const pctA = pa != null ? (pa - a.purchase_price_hkd) / a.purchase_price_hkd : -Infinity;
    const pctB = pb != null ? (pb - b.purchase_price_hkd) / b.purchase_price_hkd : -Infinity;
    return pctB - pctA;
  });

  return (
    <div className="overflow-x-auto rounded-lg border border-white/10"
         style={{ background: "rgba(15, 23, 42, 0.7)", backdropFilter: "blur(6px)" }}>
      <table className="w-full text-sm min-w-[700px]">
        <thead>
          <tr className="border-b border-white/10">
            <th className="px-3 py-2 w-[72px]" />
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wide">Card</th>
            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Bought</th>
            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Paid</th>
            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">
              Now
              <span className="ml-1 text-[10px] font-normal text-gray-600 normal-case">
                ({priceSource === "snkrdunk" ? "SNKRDunk" : "PC"})
              </span>
            </th>
            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">P&amp;L</th>
            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">30d</th>
            <th className="px-3 py-2 w-8" />
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {sorted.map((item) => {
            const now = getPrice(item, priceSource);
            const paid = item.purchase_price_hkd;
            const pnlHkd = now != null ? now - paid : null;
            const pnlPct = now != null && paid > 0 ? ((now - paid) / paid) * 100 : null;

            return (
              <tr key={item.id}
                  onClick={() => router.push(`/card/${item.card_id}`)}
                  className="hover:bg-white/5 cursor-pointer transition-colors"
                  style={{ borderLeft: `3px solid ${item.accent_color ?? "#64748b"}` }}>
                <td className="px-3 py-2">
                  {item.image_url ? (
                    <img src={item.image_url} alt={item.name} className="w-[54px] h-[76px] object-contain rounded" />
                  ) : (
                    <div className="w-[54px] h-[76px] rounded bg-white/5" />
                  )}
                </td>
                <td className="px-3 py-2">
                  <div className="font-semibold text-gray-100">{item.name}</div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {item.card_number && `${item.card_number} · `}{item.set_name}
                  </div>
                  {item.psa_population != null && (
                    <span className="text-[10px] bg-white/5 border border-white/10 rounded px-1.5 py-0.5 text-gray-400 mt-1 inline-block">
                      Pop: {item.psa_population.toLocaleString()}
                    </span>
                  )}
                </td>
                <td className="px-3 py-2 text-right text-gray-500 text-xs whitespace-nowrap">{item.purchased_at}</td>
                <td className="px-3 py-2 text-right tabular-nums text-gray-400 whitespace-nowrap">{hkd(item.purchase_price_hkd)}</td>
                <td className="px-3 py-2 text-right tabular-nums text-gray-100 font-semibold whitespace-nowrap">
                  {hkd(now)}
                </td>
                <td className="px-3 py-2 text-right whitespace-nowrap">
                  {pnlHkd != null ? (
                    <>
                      <div className={`font-bold tabular-nums ${pnlHkd >= 0 ? "text-green-400" : "text-red-400"}`}>
                        {pnlHkd >= 0 ? "+" : ""}{hkd(pnlHkd)}
                      </div>
                      <div className={`text-xs tabular-nums ${pnlPct != null && pnlPct >= 0 ? "text-green-400" : "text-red-400"}`}>
                        {pnlPct != null ? `${pnlPct >= 0 ? "+" : ""}${pnlPct.toFixed(1)}%` : ""}
                      </div>
                    </>
                  ) : <span className="text-gray-600">—</span>}
                </td>
                <td className="px-3 py-2 text-right">
                  {item.trend_1m != null ? (
                    <span className={`text-sm tabular-nums font-medium ${item.trend_1m >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {item.trend_1m >= 0 ? "▲" : "▼"}{Math.abs(item.trend_1m).toFixed(1)}%
                    </span>
                  ) : <span className="text-gray-600">—</span>}
                </td>
                <td className="px-3 py-2 text-center" onClick={(e) => handleDelete(e, item.id)}>
                  <span className="text-gray-600 hover:text-red-400 transition-colors cursor-pointer">✕</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
