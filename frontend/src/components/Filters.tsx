"use client";

import { useCallback, useState } from "react";
import type { CardFilters } from "@/lib/api";

interface Props {
  onChange: (filters: CardFilters) => void;
}

export default function Filters({ onChange }: Props) {
  const [search, setSearch] = useState("");

  const emit = useCallback(
    (overrides: Partial<{ search: string }>) => {
      const s = overrides.search ?? search;
      onChange({
        search: s || undefined,
      });
    },
    [search, onChange]
  );

  return (
    <div className="flex flex-wrap gap-3 items-end">
      <div className="flex flex-col gap-1">
        <label className="text-xs text-gray-400 uppercase tracking-wide">Search</label>
        <input
          type="text"
          placeholder="Card name…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); emit({ search: e.target.value }); }}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-100 w-52 focus:outline-none focus:border-gray-500"
        />
      </div>
    </div>
  );
}
