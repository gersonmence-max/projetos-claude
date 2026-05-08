"use client";
import Link from "next/link";
import { type Parcel, formatCurrency } from "@/lib/api";
import ScoreBadge from "./ScoreBadge";
import { ExternalLink, Star } from "lucide-react";

function StepDots({ parcel }: { parcel: Parcel }) {
  const risk = parcel.parcel_risks;
  const score = parcel.parcel_scores;
  const HIGH_FLOOD = ["A", "AE", "AO", "AH", "VE"];

  const statuses: ("ok" | "warn" | "fail" | "pend")[] = [
    "ok",
    !risk ? "pend" : (!risk.has_road_access ? "fail" : risk.road_type === "unpaved" ? "warn" : "ok"),
    !risk ? "pend" : (HIGH_FLOOD.includes((risk.flood_zone ?? "X").toUpperCase()) || risk.wetlands_percent > 50 ? "fail" : risk.tornado_risk === "high" ? "warn" : "ok"),
    !score?.market_value_estimate ? "pend" : ((score.discount_percent ?? 0) >= 40 ? "ok" : "warn"),
    score?.score_population_growth == null ? "pend" : (score.score_population_growth >= 10 ? "ok" : "warn"),
    !risk ? "pend" : (risk.has_additional_liens ? "fail" : "ok"),
    score == null ? "pend" : (score.score_total >= 70 ? "ok" : score.score_total >= 40 ? "warn" : "fail"),
  ];

  const colors = {
    ok:   "bg-gold-bright",
    warn: "bg-gold-muted",
    fail: "bg-danger",
    pend: "bg-parchment-dim/30",
  };

  return (
    <div className="flex gap-0.5 items-center" title="7 Passos do Deed Hunter (1→7)">
      {statuses.map((s, i) => (
        <div key={i} className={`w-2 h-2 rounded-full ${colors[s]}`} />
      ))}
    </div>
  );
}

interface Props {
  parcels: Parcel[];
  loading?: boolean;
}

const TYPE_LABELS: Record<string, string> = {
  land: "Terreno",
  house: "Casa",
  commercial: "Comercial",
  other: "Outro",
};

function daysUntil(dateStr: string | null): string {
  if (!dateStr) return "—";
  const diff = Math.ceil((new Date(dateStr).getTime() - Date.now()) / 86400000);
  if (diff < 0) return "Encerrado";
  if (diff === 0) return "Hoje";
  if (diff === 1) return "Amanhã";
  return `${diff} dias`;
}

function auctionClass(dateStr: string | null): string {
  if (!dateStr) return "text-parchment-muted";
  const diff = Math.ceil((new Date(dateStr).getTime() - Date.now()) / 86400000);
  if (diff <= 1) return "text-danger font-medium";
  if (diff <= 7) return "text-gold-bright";
  return "text-parchment-muted";
}

export default function ParcelTable({ parcels, loading }: Props) {
  if (loading) {
    return (
      <div className="bg-bg-card border border-[rgba(201,145,10,0.30)] rounded-lg p-8 space-y-3">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="skeleton h-10 rounded" />
        ))}
      </div>
    );
  }

  if (!parcels.length) {
    return (
      <div className="bg-bg-card border border-[rgba(201,145,10,0.25)] rounded-lg p-12 text-center">
        <div className="flex flex-col items-center gap-3">
          <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-parchment-dim"><circle cx="12" cy="12" r="10"/><path d="M16.2 7.8l-2 6.3-6.4 2.1 2-6.3z"/></svg>
          <span className="font-cinzel text-parchment-dim text-sm">Nenhuma propriedade encontrada</span>
          <span className="text-xs text-parchment-dim/60">Ajuste os filtros ou aguarde a próxima coleta</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-bg-card border border-[rgba(201,145,10,0.30)] rounded-lg overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-bg-secondary border-b border-[rgba(201,145,10,0.15)]">
            {["Endereço", "Condado/Estado", "Tipo", "Acres", "Lance mín.", "Vlr. Mercado", "Desconto", "Score", "ROI OF", "7P", "Leilão", ""].map((h) => (
              <th key={h} className="px-4 py-3 text-left text-[10px] uppercase tracking-widest text-parchment-dim font-ibm whitespace-nowrap">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {parcels.map((p) => {
            const score = p.parcel_scores;
            const dias = daysUntil(p.auction_date);
            return (
              <tr key={p.id} className="border-b border-[rgba(201,145,10,0.10)] hover:bg-gold/5 hover:border-l-2 hover:border-l-gold-bright transition-all duration-150 group">
                <td className="px-4 py-3">
                  <div className="font-ibm font-medium text-parchment truncate max-w-[220px]" title={p.address || ""}>
                    {p.address || "Sem endereço"}
                  </div>
                  {p.parcel_number && (
                    <div className="text-xs text-parchment-muted">APN: {p.parcel_number}</div>
                  )}
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <div className="text-sm text-parchment">{p.counties?.name || p.county_id}</div>
                  <div className="text-xs text-parchment-muted">{p.state}</div>
                </td>
                <td className="px-4 py-3">
                  <span className="text-xs px-2 py-0.5 border border-[rgba(201,145,10,0.30)] text-parchment-muted rounded-full">
                    {TYPE_LABELS[p.property_type] || p.property_type}
                  </span>
                </td>
                <td className="px-4 py-3 text-right font-mono text-parchment text-xs">
                  {p.acres != null ? p.acres.toFixed(2) : "—"}
                </td>
                <td className="px-4 py-3 text-right font-mono text-parchment">
                  {formatCurrency(p.minimum_bid)}
                </td>
                <td className="px-4 py-3 text-right font-mono text-parchment-muted">
                  {formatCurrency(score?.market_value_estimate)}
                </td>
                <td className="px-4 py-3 text-right font-mono text-gold-bright">
                  {score?.discount_percent != null ? `${score.discount_percent.toFixed(0)}%` : "—"}
                </td>
                <td className="px-4 py-3 text-center">
                  <ScoreBadge score={score?.score_total} />
                </td>
                <td className="px-4 py-3 text-right font-mono text-gold">
                  {score?.of_roi_percent != null ? `${score.of_roi_percent.toFixed(0)}%` : "—"}
                </td>
                <td className="px-4 py-3">
                  <StepDots parcel={p} />
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className={`text-xs ${auctionClass(p.auction_date)}`}>{dias}</span>
                  <div className="text-xs text-parchment-muted">
                    {p.auction_date ? new Date(p.auction_date).toLocaleDateString("pt-BR") : ""}
                  </div>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <div className="flex items-center gap-3">
                    <button className="text-parchment-muted hover:text-gold-bright transition-colors">
                      <Star size={16} strokeWidth={1.5} />
                    </button>
                    <Link
                      href={`/imoveis/${p.id}`}
                      className="text-parchment-muted hover:text-gold-bright transition-colors"
                    >
                      <ExternalLink size={16} strokeWidth={1.5} />
                    </Link>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
