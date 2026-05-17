// frontend/src/components/SearchBar.tsx
"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { cardsUrl } from "@/lib/api";
import type { CardSummary } from "@/lib/types";

export default function SearchBar() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CardSummary[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const search = useCallback(async (q: string) => {
    if (!q.trim()) { setResults([]); setOpen(false); return; }
    setLoading(true);
    try {
      const url = cardsUrl({ search: q, limit: 8, sort: "trend_30d" });
      const data: CardSummary[] = await fetch(url).then(r => r.json());
      setResults(Array.isArray(data) ? data : []);
      setOpen(true);
      setActiveIdx(-1);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => search(query), 280);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [query, search]);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  function navigate(card: CardSummary) {
    setQuery("");
    setResults([]);
    setOpen(false);
    router.push(`/card/${card.id}`);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (!open || results.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx(i => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx(i => Math.max(i - 1, -1));
    } else if (e.key === "Enter" && activeIdx >= 0) {
      e.preventDefault();
      navigate(results[activeIdx]);
    } else if (e.key === "Escape") {
      setOpen(false);
      inputRef.current?.blur();
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <div className="relative flex items-center">
        <svg className="absolute left-2.5 w-3.5 h-3.5 text-gray-500 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onFocus={() => { if (results.length) setOpen(true); }}
          onKeyDown={onKeyDown}
          placeholder="Search cards…"
          className="pl-8 pr-3 py-1 text-sm rounded border border-white/10 bg-white/5 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-white/30 w-44 focus:w-60 transition-all duration-200"
        />
        {loading && (
          <div className="absolute right-2.5 w-3 h-3 border border-gray-500 border-t-gray-200 rounded-full animate-spin" />
        )}
      </div>

      {open && results.length > 0 && (
        <div
          className="absolute top-full mt-1 right-0 w-72 rounded-lg border border-white/10 overflow-hidden z-50 shadow-2xl"
          style={{ background: "rgba(8, 12, 20, 0.97)", backdropFilter: "blur(12px)" }}
        >
          {results.map((card, i) => (
            <button
              key={card.id}
              onMouseDown={() => navigate(card)}
              onMouseEnter={() => setActiveIdx(i)}
              className={`w-full flex items-center gap-3 px-3 py-2 text-left transition-colors ${
                i === activeIdx ? "bg-white/10" : "hover:bg-white/5"
              }`}
            >
              {card.image_url ? (
                <img src={card.image_url} alt={card.name} className="w-8 h-11 object-contain rounded flex-shrink-0" />
              ) : (
                <div className="w-8 h-11 rounded bg-white/5 flex-shrink-0" />
              )}
              <div className="min-w-0">
                <div className="text-sm font-medium text-gray-100 truncate leading-tight">
                  {card.name}
                  {card.card_number && (
                    <span className="text-gray-500 ml-1 text-xs font-normal">#{card.card_number}</span>
                  )}
                </div>
                <div className="text-xs text-gray-500 truncate">{card.set_name}</div>
              </div>
            </button>
          ))}
        </div>
      )}

      {open && query.trim() && !loading && results.length === 0 && (
        <div
          className="absolute top-full mt-1 right-0 w-64 rounded-lg border border-white/10 px-4 py-3 text-sm text-gray-500 z-50"
          style={{ background: "rgba(8, 12, 20, 0.97)", backdropFilter: "blur(12px)" }}
        >
          No cards found for "{query}"
        </div>
      )}
    </div>
  );
}
