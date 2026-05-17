export interface CardSummary {
  id: string;
  name: string;
  set_name: string;
  card_number: string | null;
  snkrdunk_price_hkd: number | null;
  pricecharting_price_hkd: number | null;
  trend_7d: number | null;
  trend_30d: number | null;
  trend_90d: number | null;
  in_watchlist: boolean;
}

export interface SnapshotPoint {
  scraped_at: string;
  snkrdunk_price_hkd: number | null;
  pricecharting_price_hkd: number | null;
}

export interface CardDetail extends CardSummary {
  history: SnapshotPoint[];
}
