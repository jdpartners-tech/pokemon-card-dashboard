import type { CardSummary, CardDetail } from "./types";

const BASE = "/api";

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export interface CardFilters {
  search?: string;
  set?: string;
  trending_up?: boolean;
}

export function cardsUrl(filters: CardFilters): string {
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.set) params.set("set", filters.set);
  if (filters.trending_up) params.set("trending_up", "true");
  const qs = params.toString();
  return `${BASE}/cards${qs ? `?${qs}` : ""}`;
}

export const fetchCards = (url: string) => json<CardSummary[]>(url);
export const fetchWatchlist = () => json<CardSummary[]>(`${BASE}/watchlist`);
export const fetchCard = (id: string) => json<CardDetail>(`${BASE}/cards/${id}`);

export async function addToWatchlist(cardId: string): Promise<void> {
  await json(`${BASE}/watchlist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ card_id: cardId }),
  });
}

export async function removeFromWatchlist(cardId: string): Promise<void> {
  await json(`${BASE}/watchlist/${cardId}`, { method: "DELETE" });
}

export async function triggerScrape(): Promise<void> {
  await json(`${BASE}/admin/scrape`, { method: "POST" });
}

export async function triggerBackfill(): Promise<void> {
  await json(`${BASE}/admin/backfill`, { method: "POST" });
}

export async function triggerSnkrdunkBackfill(): Promise<void> {
  await json(`${BASE}/admin/backfill/snkrdunk`, { method: "POST" });
}

export const reportUrl = `${BASE}/report`;
