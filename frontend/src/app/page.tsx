// frontend/src/app/page.tsx
"use client";

import { useState, useRef, useEffect } from "react";
import useSWR from "swr";
import { cardsUrl, fetchCards, type CardFilters } from "@/lib/api";
import CardTable from "@/components/CardTable";

const SORT_OPTIONS: { value: NonNullable<CardFilters["sort"]>; label: string }[] = [
  { value: "trend_1m",  label: "Trend: 1M"   },
  { value: "trend_3m",  label: "Trend: 3M"   },
  { value: "trend_6m",  label: "Trend: 6M"   },
  { value: "trend_all", label: "Trend: All"  },
  { value: "price_hkd", label: "Price (HKD)" },
  { value: "name",      label: "Name (A–Z)"  },
];

function SortDropdown({
  value,
  onChange,
}: {
  value: NonNullable<CardFilters["sort"]>;
  onChange: (v: NonNullable<CardFilters["sort"]>) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const current = SORT_OPTIONS.find(o => o.value === value) ?? SORT_OPTIONS[0];

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 bg-white/5 border border-white/10 rounded px-3 py-1.5 text-sm text-gray-100 hover:border-white/30 focus:outline-none transition-colors"
      >
        {current.label}
        <svg className={`w-3.5 h-3.5 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div
          className="absolute right-0 top-full mt-1 w-44 rounded-lg border border-white/10 overflow-hidden z-40 shadow-2xl"
          style={{ background: "rgba(8, 12, 20, 0.97)", backdropFilter: "blur(12px)" }}
        >
          {SORT_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onMouseDown={() => { onChange(opt.value); setOpen(false); }}
              className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                opt.value === value
                  ? "text-blue-400 bg-blue-500/10"
                  : "text-gray-300 hover:bg-white/5"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function HomePage() {
  const [filters, setFilters] = useState<CardFilters>({ sort: "trend_1m" });
  const url = cardsUrl(filters);
  const { data, error, isLoading } = useSWR(url, fetchCards, { refreshInterval: 60_000 });

  const currentSortLabel = SORT_OPTIONS.find(o => o.value === filters.sort)?.label ?? "Trend: 30d";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-100">Top Trending PSA 10 Cards</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {data ? `${data.length} cards` : "Loading…"} · sorted by {currentSortLabel}
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <SortDropdown
            value={filters.sort ?? "trend_1m"}
            onChange={(sort) => setFilters(f => ({ ...f, sort }))}
          />
          <label className="flex items-center gap-2 cursor-pointer select-none text-sm text-gray-400 hover:text-gray-200 transition-colors">
            <input
              type="checkbox"
              checked={!!filters.positive_only}
              onChange={(e) => setFilters(f => ({ ...f, positive_only: e.target.checked || undefined }))}
              className="accent-green-400 w-3.5 h-3.5"
            />
            Trending ↑ only
          </label>
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-red-950/60 border border-red-800/60 px-4 py-3 text-sm text-red-300 backdrop-blur">
          Failed to load cards — is the backend running?
        </div>
      )}
      {isLoading && (
        <div className="text-center py-16 text-gray-500 animate-pulse">Loading cards…</div>
      )}
      {data && <CardTable cards={data} activeSort={filters.sort ?? "trend_1m"} />}
    </div>
  );
}
