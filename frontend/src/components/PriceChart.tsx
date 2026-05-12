"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { SnapshotPoint } from "@/lib/types";

interface Props {
  history: SnapshotPoint[];
}

export default function PriceChart({ history }: Props) {
  if (history.length === 0) {
    return <div className="text-center py-12 text-gray-500">No price history yet.</div>;
  }

  const data = history.map((p) => ({
    date: new Date(p.scraped_at).toLocaleDateString("en-HK", { month: "short", day: "numeric" }),
    snkrdunk: p.snkrdunk_price_hkd,
    pricecharting: p.pricecharting_price_hkd,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="date" tick={{ fill: "#9ca3af", fontSize: 12 }} />
        <YAxis
          tick={{ fill: "#9ca3af", fontSize: 12 }}
          tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
          width={52}
        />
        <Tooltip
          contentStyle={{ background: "#1f2937", border: "1px solid #374151", borderRadius: 6 }}
          labelStyle={{ color: "#e5e7eb" }}
          formatter={(v: number) =>
            [`HK$${v.toLocaleString("en-HK", { maximumFractionDigits: 0 })}`, ""]
          }
        />
        <Legend wrapperStyle={{ color: "#9ca3af", fontSize: 13 }} />
        <Line
          type="monotone"
          dataKey="snkrdunk"
          name="Snkrdunk (HKD)"
          stroke="#60a5fa"
          strokeWidth={2}
          dot={false}
          connectNulls
        />
        <Line
          type="monotone"
          dataKey="pricecharting"
          name="PriceCharting (HKD)"
          stroke="#f59e0b"
          strokeWidth={2}
          dot={false}
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
