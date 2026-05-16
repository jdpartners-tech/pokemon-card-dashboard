"use client";

import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, ReferenceLine,
} from "recharts";
import type { SnapshotPoint } from "@/lib/types";

type Range = "1W" | "1M" | "3M" | "ALL";

const RANGE_DAYS: Record<Range, number> = { "1W": 7, "1M": 30, "3M": 90, "ALL": Infinity };

interface Props {
  history: SnapshotPoint[];
}

export default function PriceChart({ history }: Props) {
  const [range, setRange] = useState<Range>("3M");

  if (history.length === 0) {
    return <div className="text-center py-12 text-gray-500">No price history yet.</div>;
  }

  const maxDays = RANGE_DAYS[range];
  const now = Date.now();
  const filtered = history.filter((p) => {
    const daysAgo = (now - new Date(p.scraped_at).getTime()) / 86_400_000;
    return daysAgo <= maxDays;
  });

  const data = filtered.map((p) => ({
    date: new Date(p.scraped_at).toLocaleDateString("en-HK", {
      year: filtered.length > 60 ? "2-digit" : undefined,
      month: "short",
      day: filtered.length <= 14 ? "numeric" : undefined,
    }),
    snkrdunk: p.snkrdunk_price_hkd,
    pricecharting: p.pricecharting_price_hkd,
  }));

  if (data.length === 0) {
    return <div className="text-center py-12 text-gray-500">No data in this time range.</div>;
  }

  return (
    <div>
      {/* Range tabs */}
      <div className="flex gap-1 mb-4">
        {(["1W", "1M", "3M", "ALL"] as Range[]).map((r) => (
          <button
            key={r}
            onClick={() => setRange(r)}
            className={`px-3 py-1 text-xs rounded font-medium transition-colors ${
              range === r
                ? "bg-blue-600 text-white"
                : "bg-gray-800 text-gray-400 hover:text-gray-200"
            }`}
          >
            {r}
          </button>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis
            dataKey="date"
            tick={{ fill: "#6b7280", fontSize: 11 }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: "#6b7280", fontSize: 11 }}
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
            width={48}
          />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 6 }}
            labelStyle={{ color: "#e5e7eb", fontSize: 12 }}
            formatter={(v: number, name: string) => [
              `HK$${v.toLocaleString("en-HK", { maximumFractionDigits: 0 })}`,
              name === "snkrdunk" ? "Snkrdunk" : "PriceCharting",
            ]}
          />
          <Line
            type="monotone"
            dataKey="pricecharting"
            name="pricecharting"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="snkrdunk"
            name="snkrdunk"
            stroke="#60a5fa"
            strokeWidth={2}
            dot={data.length <= 14}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>

      <div className="flex items-center gap-4 mt-2 justify-center text-xs text-gray-500">
        <span className="flex items-center gap-1.5">
          <span className="w-4 h-0.5 bg-amber-400 inline-block" /> PriceCharting (HKD)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-4 h-0.5 bg-blue-400 inline-block" /> Snkrdunk (HKD)
        </span>
      </div>
    </div>
  );
}
