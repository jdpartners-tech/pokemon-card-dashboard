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
  min_score?: number;
}

export function cardsUrl(filters: CardFilters): string {
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.set) params.set("set", filters.set);
  if (filters.min_score != null) params.set("min_score", String(filters.min_score));
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

export const reportUrl = `${BASE}/report`;
