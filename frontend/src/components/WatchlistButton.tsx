"use client";

import { useState } from "react";
import { addToWatchlist, removeFromWatchlist } from "@/lib/api";

interface Props {
  cardId: string;
  inWatchlist: boolean;
  onToggle?: (nowIn: boolean) => void;
}

export default function WatchlistButton({ cardId, inWatchlist, onToggle }: Props) {
  const [active, setActive] = useState(inWatchlist);
  const [loading, setLoading] = useState(false);

  async function toggle() {
    setLoading(true);
    try {
      if (active) {
        await removeFromWatchlist(cardId);
        setActive(false);
        onToggle?.(false);
      } else {
        await addToWatchlist(cardId);
        setActive(true);
        onToggle?.(true);
      }
    } catch {
      // keep current state on error
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      onClick={(e) => { e.stopPropagation(); toggle(); }}
      disabled={loading}
      title={active ? "Remove from watchlist" : "Add to watchlist"}
      className={`text-lg leading-none transition-colors disabled:opacity-40 ${
        active ? "text-yellow-400 hover:text-yellow-200" : "text-gray-600 hover:text-yellow-400"
      }`}
    >
      ★
    </button>
  );
}
