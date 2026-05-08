export interface AiAnalysis {
  resumo: string;
  pontos_positivos: string[];
  pontos_atencao: string[];
  veredicto: "Oportunidade forte" | "Merece análise" | "Cautela";
}

export interface ScoreBreakdown {
  a_pts: number;
  b_pts: number;
  c_pts: number;
}

export interface Property {
  id: number;
  source: string;
  state: string;
  county: string;
  address: string;
  lat: number | null;
  lng: number | null;
  price: number | null;
  acres: number | null;
  price_per_acre: number | null;
  discount_pct: number | null;
  fema_zone: string | null;
  score: number | null;
  classification: "FORTE" | "MODERADO" | "FRACO" | "EVITAR" | null;
  score_breakdown?: ScoreBreakdown;
  ai_analysis?: AiAnalysis | null;
  listing_url: string;
  parcel_id: string | null;
  sale_date: string | null;
  scraped_at: string | null;
  passed_filters: boolean;
  population?: number;
  median_hh_income?: number;
}

export interface PipelineRun {
  id: number;
  status: "rodando" | "concluído" | "erro";
  started_at: string | null;
  finished_at: string | null;
  scraped: number;
  enriched: number;
  filtered: number;
  scored: number;
  error_msg: string | null;
}

export interface PropertyFilters {
  state?: string;
  county?: string;
  classification?: string;
  min_score?: number;
  max_price?: number;
  min_acres?: number;
  max_price_per_acre?: number;
  min_discount_pct?: number;
}
