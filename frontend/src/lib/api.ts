// frontend/src/lib/api.ts
import type { CardSummary, CardDetail, PortfolioSummary } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const fetcher = (url: string) => fetch(url).then((r) => r.json());

export interface CardFilters {
  search?: string;
  sort?: "trend_7d" | "trend_30d" | "trend_90d" | "trend_1y";
  limit?: number;
}

export function cardsUrl(f: CardFilters = {}): string {
  const p = new URLSearchParams();
  if (f.search) p.set("search", f.search);
  if (f.sort) p.set("sort", f.sort);
  if (f.limit) p.set("limit", String(f.limit));
  return `${BASE}/cards?${p}`;
}

export const fetchCards = (url: string): Promise<CardSummary[]> => fetcher(url);
export const fetchCard = (id: string): Promise<CardDetail> =>
  fetcher(`${BASE}/cards/${id}`);
export const fetchPortfolio = (): Promise<PortfolioSummary> =>
  fetcher(`${BASE}/portfolio`);

export async function addPortfolioItem(body: {
  card_id: string;
  purchase_price_hkd: number;
  purchased_at: string;
}): Promise<{ ok: boolean; id: string }> {
  const r = await fetch(`${BASE}/portfolio`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return r.json();
}

export async function deletePortfolioItem(id: string): Promise<void> {
  await fetch(`${BASE}/portfolio/${id}`, { method: "DELETE" });
}

export async function toggleWatchlist(
  cardId: string, inWatchlist: boolean
): Promise<void> {
  if (inWatchlist) {
    await fetch(`${BASE}/watchlist/${cardId}`, { method: "DELETE" });
  } else {
    await fetch(`${BASE}/watchlist`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ card_id: cardId }),
    });
  }
}
