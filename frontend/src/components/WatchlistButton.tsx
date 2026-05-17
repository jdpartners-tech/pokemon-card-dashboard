"use client";
import { useState } from "react";
import { toggleWatchlist } from "@/lib/api";

interface Props {
  cardId: string;
  inWatchlist: boolean;
  onToggle?: (nowIn: boolean) => void;
}

export default function WatchlistButton({ cardId, inWatchlist, onToggle }: Props) {
  const [active, setActive] = useState(inWatchlist);

  async function handle() {
    await toggleWatchlist(cardId, active);
    const next = !active;
    setActive(next);
    onToggle?.(next);
  }

  return (
    <button onClick={handle} className="text-lg leading-none transition-colors hover:scale-110">
      {active ? "★" : "☆"}
    </button>
  );
}
