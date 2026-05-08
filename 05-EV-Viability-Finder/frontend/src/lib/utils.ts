import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number | null | undefined): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatAcres(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value.toFixed(1)} ac`;
}

export function formatDiscount(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value.toFixed(1)}%`;
}

export function scoreColor(score: number | null | undefined): string {
  if (score == null) return "text-text-muted";
  if (score >= 70) return "text-score-high";
  if (score >= 40) return "text-score-mid";
  return "text-score-low";
}

export function scoreBg(score: number | null | undefined): string {
  if (score == null) return "bg-surface";
  if (score >= 70) return "bg-score-high/10 border-score-high/30";
  if (score >= 40) return "bg-score-mid/10 border-score-mid/30";
  return "bg-score-low/10 border-score-low/30";
}

export function buildGoogleMapsUrl(address: string): string {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`;
}

export function buildStreetViewUrl(
  lat: number | null,
  lng: number | null,
  address?: string
): string {
  if (lat && lng) {
    return `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${lat},${lng}`;
  }
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address ?? "")}`;
}

export function formatSaleDate(value: string | null | undefined): string {
  if (!value) return "—";
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}
