"use client";
import { useQuery } from "@tanstack/react-query";
import { fetchParcel, fetchParcelLiens, saveParcel, formatCurrency } from "@/lib/api";
import ScoreBadge from "@/components/ScoreBadge";
import RiskBadges from "@/components/RiskBadges";
import OwnerFinancingCalc from "@/components/OwnerFinancingCalc";
import DeedHunterSteps from "@/components/DeedHunterSteps";
import LiensPanel from "@/components/LiensPanel";
import FloodRiskPanel from "@/components/FloodRiskPanel";
import Link from "next/link";
import { useState } from "react";

const TYPE_LABELS: Record<string, string> = {
  land: "Terreno", house: "Casa", commercial: "Comercial", other: "Outro",
};

const AI_COLORS: Record<string, string> = {
  comprar: "bg-green-50 border-green-200 text-green-800",
  monitorar: "bg-yellow-50 border-yellow-200 text-yellow-800",
  ignorar: "bg-red-50 border-red-200 text-red-700",
};

export default function ParcelDetailPage({ params }: { params: { id: string } }) {
  const { data: parcel, isLoading } = useQuery({
    queryKey: ["parcel", params.id],
    queryFn: () => fetchParcel(params.id),
  });

  const { data: liens } = useQuery({
    queryKey: ["liens", params.id],
    queryFn: () => fetchParcelLiens(params.id),
    enabled: !!parcel,
  });

  const [saved, setSaved] = useState(false);

  if (isLoading) {
    return <div className="text-center py-20 text-gray-400">Carregando imóvel...</div>;
  }
  if (!parcel) {
    return <div className="text-center py-20 text-gray-500">Imóvel não encontrado.</div>;
  }

  const score = parcel.parcel_scores;
  const risk = parcel.parcel_risks;
  const county = parcel.counties;

  async function handleSave() {
    await saveParcel(parcel!.id);
    setSaved(true);
  }

  return (
    <div className="max-w-5xl">
      {/* Header */}
      <div className="flex items-start justify-between mb-5">
        <div>
          <Link href="/imoveis" className="text-sm text-blue-600 hover:underline mb-2 block">
            ← Voltar para imóveis
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">{parcel.address || "Sem endereço"}</h1>
          <p className="text-gray-500 mt-1">
            {county?.name}, {parcel.state} {parcel.zip && `· CEP ${parcel.zip}`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <ScoreBadge score={score?.score_total} />
          <button
            onClick={handleSave}
            disabled={saved}
            className={`text-sm px-4 py-2 rounded-lg border transition-colors ${
              saved
                ? "bg-yellow-50 border-yellow-200 text-yellow-700"
                : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
            }`}
          >
            {saved ? "⭐ Salvo" : "Salvar imóvel"}
          </button>
          <a
            href={parcel.auction_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Ver leilão ↗
          </a>
          {parcel.gps_lat && parcel.gps_lng && (
            <>
              <a
                href={`https://www.google.com/maps/search/?api=1&query=${parcel.gps_lat},${parcel.gps_lng}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Google Maps ↗
              </a>
              <a
                href={`https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${parcel.gps_lat},${parcel.gps_lng}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700"
              >
                Street View ↗
              </a>
            </>
          )}
        </div>
      </div>

      {/* Risk badges */}
      {risk && (
        <div className="mb-5">
          <RiskBadges risk={risk} />
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* 7 PASSOS DO MÉTODO DEED HUNTER — destaque principal               */}
      {/* ═══════════════════════════════════════════════════════════════════ */}
      <DeedHunterSteps parcel={parcel} liens={liens ?? null} />

      {/* Key metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: "Lance mínimo", value: formatCurrency(parcel.minimum_bid) },
          { label: "Valor de mercado", value: formatCurrency(score?.market_value_estimate) },
          { label: "Desconto", value: score?.discount_percent != null ? `${score.discount_percent.toFixed(0)}%` : "—" },
          { label: "ROI Owner Financing", value: score?.of_roi_percent != null ? `${score.of_roi_percent.toFixed(0)}%` : "—" },
          { label: "Tipo", value: TYPE_LABELS[parcel.property_type] || parcel.property_type },
          { label: "Área", value: parcel.acres != null ? `${parcel.acres.toFixed(2)} acres` : "—" },
          { label: "Data do leilão", value: parcel.auction_date ? new Date(parcel.auction_date).toLocaleDateString("pt-BR") : "—" },
          { label: "Plataforma", value: parcel.auction_platform },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-xs text-gray-500">{label}</div>
            <div className="text-base font-semibold text-gray-900 mt-1">{value}</div>
          </div>
        ))}
      </div>

      {/* Owner Financing Calculator */}
      {score?.market_value_estimate && parcel.minimum_bid && (
        <div className="mb-6">
          <OwnerFinancingCalc
            minimumBid={parcel.minimum_bid}
            marketValue={score.market_value_estimate}
          />
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* PASSO 6 — Liens Detail Panel                                      */}
      {/* ═══════════════════════════════════════════════════════════════════ */}
      <div className="mb-6">
        {liens ? (
          <LiensPanel
            liens={liens}
            clerkUrl={liens.records[0]?.clerk_portal_url ?? undefined}
          />
        ) : (
          <div className="bg-gray-50 rounded-xl border border-dashed border-gray-300 p-5 text-center text-sm text-gray-400">
            Passo 6 — Pesquisa no Clerk&apos;s Office pendente (executar pipeline)
          </div>
        )}
      </div>

      {/* Flood Risk Panel detalhado */}
      {risk && (
        <div className="mb-6">
          <FloodRiskPanel risk={risk} />
        </div>
      )}

      {/* Property details + Risk details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-3">Detalhes do imóvel</h3>
          <dl className="space-y-2 text-sm">
            {[
              ["Número APN", parcel.parcel_number],
              ["Cidade", parcel.city],
              ["CEP", parcel.zip],
              ["Zoneamento", parcel.zoning],
              parcel.bedrooms != null && ["Quartos", parcel.bedrooms],
              parcel.bathrooms != null && ["Banheiros", parcel.bathrooms],
              parcel.sqft != null && ["Área construída", `${parcel.sqft.toLocaleString("pt-BR")} sqft`],
              parcel.year_built != null && ["Ano de construção", parcel.year_built],
              parcel.gps_lat != null && ["Coordenadas", `${parcel.gps_lat.toFixed(5)}, ${parcel.gps_lng?.toFixed(5)}`],
            ].filter((x): x is [string, string | number] => Array.isArray(x) && !!x[1]).map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <dt className="text-gray-500">{k}</dt>
                <dd className="font-medium">{String(v)}</dd>
              </div>
            ))}
          </dl>
        </div>

        {risk && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-3">Dados de risco</h3>
            <dl className="space-y-2 text-sm">
              {[
                ["Flood zone (FEMA)", risk.flood_zone],
                ["Wetlands", `${risk.wetlands_percent?.toFixed(0) ?? 0}%`],
                ["Risco tornado", risk.tornado_risk],
                ["Acesso", risk.road_type === "paved" ? "Pavimentada" : risk.road_type === "unpaved" ? "Não pavimentada" : "Sem acesso"],
                ["Cidade mais próxima", risk.nearest_city],
                ["Distância", risk.nearest_city_distance_miles != null ? `${risk.nearest_city_distance_miles} mi` : "—"],
                ["Tempo de direção", risk.drive_time_minutes != null ? `${risk.drive_time_minutes} min` : "—"],
                ["Liens sobreviventes", risk.has_additional_liens ? `Sim — ${formatCurrency(risk.liens_amount)}` : "Nenhum"],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <dt className="text-gray-500">{k}</dt>
                  <dd className={`font-medium ${k === "Liens sobreviventes" && risk.has_additional_liens ? "text-red-600" : ""}`}>
                    {v || "—"}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </div>

      {/* Score breakdown */}
      {score && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
          <h3 className="font-semibold text-gray-900 mb-4">Breakdown do score</h3>
          <div className="space-y-3">
            {[
              { label: "Desconto sobre mercado", pts: score.score_discount, max: 40 },
              { label: "Crescimento populacional", pts: score.score_population_growth, max: 20 },
              { label: "Acesso por estrada", pts: score.score_road_access, max: 20 },
              { label: "Tamanho e usabilidade", pts: score.score_size, max: 10 },
              { label: "Lance mínimo", pts: score.score_bid_price, max: 10 },
            ].map(({ label, pts, max }) => (
              <div key={label}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">{label}</span>
                  <span className="font-medium">{pts}/{max} pts</span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full">
                  <div
                    className="h-2 bg-blue-500 rounded-full transition-all"
                    style={{ width: `${(pts / max) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-4 border-t border-gray-100 flex justify-between items-center">
            <span className="font-semibold text-gray-900">Total</span>
            <ScoreBadge score={score.score_total} />
          </div>
        </div>
      )}

      {/* Map */}
      {parcel.gps_lat && parcel.gps_lng && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
          <h3 className="font-semibold text-gray-900 mb-3">Localização</h3>
          <div className="bg-gray-100 rounded-lg h-48 flex items-center justify-center text-sm">
            <a
              href={`https://www.openstreetmap.org/?mlat=${parcel.gps_lat}&mlon=${parcel.gps_lng}&zoom=14`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline"
            >
              Ver no OpenStreetMap ({parcel.gps_lat.toFixed(5)}, {parcel.gps_lng.toFixed(5)}) ↗
            </a>
          </div>
        </div>
      )}

      {/* AI Analysis */}
      {score?.ai_analysis && (
        <div className={`rounded-xl border p-5 mb-6 ${AI_COLORS[score.ai_recommendation || "monitorar"]}`}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold">Análise por IA — Passo 7</h3>
            <span className={`text-xs px-3 py-1 rounded-full font-bold uppercase border ${AI_COLORS[score.ai_recommendation || "monitorar"]}`}>
              {score.ai_recommendation === "comprar" ? "COMPRAR" :
               score.ai_recommendation === "ignorar" ? "IGNORAR" : "MONITORAR"}
            </span>
          </div>
          <div className="text-sm whitespace-pre-line leading-relaxed">
            {score.ai_analysis}
          </div>
          {score.ai_analyzed_at && (
            <div className="text-xs opacity-60 mt-3">
              Analisado em {new Date(score.ai_analyzed_at).toLocaleString("pt-BR")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
