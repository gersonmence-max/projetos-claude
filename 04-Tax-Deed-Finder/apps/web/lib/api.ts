import axios from "axios";

const BASE = process.env.NEXT_PUBLIC_API_URL || "https://landhq-production.up.railway.app";

export const api = axios.create({ baseURL: BASE });

export interface County {
  id: string;
  name: string;
  state: string;
  auction_platform: string;
  active: boolean;
}

export interface ParcelScore {
  score_total: number;
  score_discount: number;
  score_population_growth: number;
  score_road_access: number;
  score_size: number;
  score_bid_price: number;
  market_value_estimate: number | null;
  discount_percent: number | null;
  of_resale_price: number | null;
  of_down_payment: number | null;
  of_monthly_payment: number | null;
  of_term_months: number | null;
  of_total_return: number | null;
  of_roi_percent: number | null;
  of_months_to_recover: number | null;
  ai_recommendation: string | null;
  ai_analyzed_at: string | null;
  ai_analysis?: string | null;
}

export interface ParcelRisk {
  flood_zone: string;
  wetlands_percent: number;
  tornado_risk: string;
  has_road_access: boolean;
  road_type: string;
  nearest_city: string | null;
  nearest_city_distance_miles: number | null;
  drive_time_minutes: number | null;
  passes_auto_filters: boolean;
  has_additional_liens: boolean;
  liens_amount: number;
}

export interface LienRecord {
  id: string;
  parcel_id: string;
  lien_type: string;
  grantor: string | null;
  grantee: string | null;
  lien_amount: number | null;
  recorded_date: string | null;
  is_released: boolean;
  release_doc_number: string | null;
  release_date: string | null;
  survives_tax_deed: boolean;
  survive_reason: string | null;
  clerk_portal_url: string | null;
  source: string | null;
}

export interface LiensResponse {
  records: LienRecord[];
  total: number;
  active: number;
  surviving: number;
  surviving_amount: number;
  surviving_types: string[];
}

export async function fetchParcelLiens(parcelId: string): Promise<LiensResponse> {
  const { data } = await api.get(`/api/parcels/${parcelId}/liens`);
  return data;
}

export interface Parcel {
  id: string;
  external_id: string;
  parcel_number: string | null;
  address: string | null;
  city: string | null;
  state: string;
  zip: string | null;
  property_type: string;
  acres: number | null;
  sqft: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  year_built: number | null;
  zoning: string | null;
  gps_lat: number | null;
  gps_lng: number | null;
  auction_platform: string;
  auction_url: string;
  minimum_bid: number;
  auction_date: string | null;
  auction_status: string;
  county_id: string;
  counties: County | null;
  parcel_scores: ParcelScore | null;
  parcel_risks: ParcelRisk | null;
}

export interface DashboardSummary {
  total_monitored: number;
  new_today: number;
  score_70_plus: number;
  auctions_next_7_days: number;
}

export interface ParcelsResponse {
  items: Parcel[];
  total: number;
  page: number;
  page_size: number;
}

export interface FilterParams {
  state?: string;
  county_id?: string;
  property_type?: string;
  min_score?: number;
  max_score?: number;
  min_bid?: number;
  max_bid?: number;
  min_acres?: number;
  max_acres?: number;
  road_type?: string;
  max_drive_time?: number;
  min_discount?: number;
  min_roi?: number;
  has_ai_analysis?: boolean;
  order_by?: string;
  order_dir?: string;
  page?: number;
  page_size?: number;
}

export async function fetchParcels(params: FilterParams): Promise<ParcelsResponse> {
  const { data } = await api.get("/api/parcels", { params });
  return data;
}

export async function fetchParcel(id: string): Promise<Parcel> {
  const { data } = await api.get(`/api/parcels/${id}`);
  return data;
}

export async function fetchSummary(): Promise<DashboardSummary> {
  const { data } = await api.get("/api/dashboard/summary");
  return data;
}

export async function fetchCounties(): Promise<County[]> {
  const { data } = await api.get("/api/counties");
  return data;
}

export async function fetchSaved() {
  const { data } = await api.get("/api/saved");
  return data;
}

export async function saveParcel(parcel_id: string, notes?: string) {
  const { data } = await api.post("/api/saved", { parcel_id, notes });
  return data;
}

export async function removeSaved(saved_id: string) {
  await api.delete(`/api/saved/${saved_id}`);
}

export async function fetchAnalytics() {
  const { data } = await api.get("/api/analytics");
  return data;
}

export async function toggleCounty(county_id: string, active: boolean) {
  await api.patch(`/api/counties/${county_id}`, null, { params: { active } });
}

export async function triggerPipeline() {
  const { data } = await api.post("/api/pipeline/run");
  return data;
}

// Helpers
export function formatCurrency(value: number | null | undefined): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
}

export function formatNumber(value: number | null | undefined, decimals = 0): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: decimals }).format(value);
}

export function scoreColor(score: number): string {
  if (score >= 75) return "text-green-600 bg-green-50";
  if (score >= 50) return "text-yellow-600 bg-yellow-50";
  return "text-gray-500 bg-gray-50";
}

export function floodZoneColor(zone: string): string {
  const z = zone?.toUpperCase();
  if (["A", "AE", "AO", "AH", "VE"].includes(z)) return "bg-red-100 text-red-700";
  if (z === "X") return "bg-green-100 text-green-700";
  return "bg-gray-100 text-gray-600";
}

export function tornadoColor(risk: string): string {
  if (risk === "high") return "bg-red-100 text-red-700";
  if (risk === "medium") return "bg-yellow-100 text-yellow-700";
  return "bg-green-100 text-green-700";
}
