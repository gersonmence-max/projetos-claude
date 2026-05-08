import type { Property, PropertyFilters } from "../types";
import client from "./client";

export async function fetchProperties(filters: PropertyFilters = {}): Promise<Property[]> {
  const params: Record<string, string | number> = {};
  if (filters.state) params.state = filters.state;
  if (filters.county) params.county = filters.county;
  if (filters.classification) params.classification = filters.classification;
  if (filters.min_score != null) params.min_score = filters.min_score;
  if (filters.max_price != null) params.max_price = filters.max_price;
  if (filters.min_acres != null) params.min_acres = filters.min_acres;
  if (filters.max_price_per_acre != null) params.max_price_per_acre = filters.max_price_per_acre;
  if (filters.min_discount_pct != null) params.min_discount_pct = filters.min_discount_pct;

  const { data } = await client.get<Property[]>("/properties/", { params });
  return data;
}

export async function fetchProperty(id: number): Promise<Property> {
  const { data } = await client.get<Property>(`/properties/${id}`);
  return data;
}
