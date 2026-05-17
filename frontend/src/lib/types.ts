// frontend/src/lib/types.ts
export interface CardSummary {
  id: string;
  name: string;
  set_name: string;
  card_number: string | null;
  image_url: string | null;
  accent_color: string | null;
  snkrdunk_price_hkd: number | null;
  pricecharting_price_hkd: number | null;
  psa_population: number | null;
  trend_7d: number | null;
  trend_30d: number | null;
  trend_90d: number | null;
  trend_1y: number | null;
  pct_from_ath: number | null;
  trend_consistency: number;
  in_watchlist: boolean;
}

export interface SnapshotPoint {
  scraped_at: string;
  snkrdunk_price_hkd: number | null;
  pricecharting_price_hkd: number | null;
}

export interface CardDetail extends CardSummary {
  snkrdunk_url: string | null;
  pricecharting_url: string | null;
  sales_per_day: number | null;
  ath: number | null;
  ath_date: string | null;
  history: SnapshotPoint[];
}

export interface PortfolioItem {
  id: string;
  card_id: string;
  name: string;
  set_name: string;
  card_number: string | null;
  image_url: string | null;
  accent_color: string | null;
  psa_population: number | null;
  purchase_price_hkd: number;
  purchased_at: string;
  current_price_hkd: number | null;
  pnl_hkd: number | null;
  pnl_pct: number | null;
  trend_30d: number | null;
}

export interface PortfolioSummary {
  items: PortfolioItem[];
  total_invested: number;
  total_current_value: number;
  total_pnl_hkd: number;
  total_pnl_pct: number | null;
}
