"use client";
import type { Parcel, LiensResponse } from "@/lib/api";

type StepStatus = "ok" | "warning" | "fail" | "pending";

interface Step {
  number: number;
  label: string;
  sublabel: string;
  status: StepStatus;
  detail: string;
  icon: string;
}

const STATUS_STYLES: Record<StepStatus, { ring: string; bg: string; text: string; icon: string }> = {
  ok:      { ring: "ring-green-400",  bg: "bg-green-500",  text: "text-green-700",  icon: "✓" },
  warning: { ring: "ring-yellow-400", bg: "bg-yellow-400", text: "text-yellow-700", icon: "!" },
  fail:    { ring: "ring-red-400",    bg: "bg-red-500",    text: "text-red-700",    icon: "✕" },
  pending: { ring: "ring-gray-300",   bg: "bg-gray-300",   text: "text-gray-500",   icon: "?" },
};

const LIEN_TYPE_LABELS: Record<string, string> = {
  irs_federal: "IRS Federal",
  state_tax: "Imposto Estadual",
  hoa: "HOA",
  hospital: "Hospitalar",
  code_enforcement: "Código Municipal",
  judgment: "Judicial",
  mechanics: "Empreiteiro",
  other: "Outro",
};

function buildSteps(parcel: Parcel, liens: LiensResponse | null): Step[] {
  const risk = parcel.parcel_risks;
  const score = parcel.parcel_scores;

  // ── Passo 1: Identificado ─────────────────────────────────────────────────
  const step1: Step = {
    number: 1,
    label: "Identificado",
    sublabel: "Leilão encontrado",
    icon: "🔍",
    status: "ok",
    detail: `${parcel.auction_platform} · Lance mín. $${(parcel.minimum_bid ?? 0).toLocaleString("pt-BR")} · ${parcel.auction_date ? new Date(parcel.auction_date).toLocaleDateString("pt-BR") : "data N/A"}`,
  };

  // ── Passo 2: Acesso Físico ────────────────────────────────────────────────
  let step2Status: StepStatus = "pending";
  let step2Detail = "Acesso não verificado";
  if (risk) {
    if (!risk.has_road_access || risk.road_type === "none") {
      step2Status = "fail";
      step2Detail = "Sem acesso por estrada — imóvel excluído";
    } else if (risk.road_type === "unpaved") {
      step2Status = "warning";
      step2Detail = `Estrada de terra · ${risk.nearest_city_distance_miles ?? "?"} mi de ${risk.nearest_city ?? "cidade"} · ${risk.drive_time_minutes ?? "?"} min`;
    } else {
      step2Status = "ok";
      step2Detail = `Estrada pavimentada · ${risk.nearest_city_distance_miles ?? "?"} mi de ${risk.nearest_city ?? "cidade"} · ${risk.drive_time_minutes ?? "?"} min`;
    }
    if (risk.drive_time_minutes != null && risk.drive_time_minutes > 90) {
      if (step2Status === "ok") step2Status = "warning";
      step2Detail += " ⚠ distância elevada";
    }
  }
  const step2: Step = {
    number: 2, label: "Acesso", sublabel: "Chegamos ao terreno?",
    icon: "🚗", status: step2Status, detail: step2Detail,
  };

  // ── Passo 3: Risco Natural ────────────────────────────────────────────────
  let step3Status: StepStatus = "pending";
  let step3Detail = "Risco natural não verificado";
  if (risk) {
    const HIGH_FLOOD = ["A", "AE", "AO", "AH", "VE"];
    const floodFail = HIGH_FLOOD.includes((risk.flood_zone ?? "X").toUpperCase());
    const wetlandsFail = risk.wetlands_percent > 50;
    const tornadoHigh = risk.tornado_risk === "high";

    if (floodFail || wetlandsFail) {
      step3Status = "fail";
      step3Detail = [
        floodFail ? `Flood zone ${risk.flood_zone} (alto risco)` : null,
        wetlandsFail ? `${risk.wetlands_percent.toFixed(0)}% wetlands` : null,
      ].filter(Boolean).join(" · ");
    } else if (tornadoHigh || risk.wetlands_percent > 20) {
      step3Status = "warning";
      step3Detail = [
        tornadoHigh ? "Tornado risk alto" : null,
        risk.wetlands_percent > 20 ? `${risk.wetlands_percent.toFixed(0)}% wetlands` : null,
        `Flood zone ${risk.flood_zone}`,
      ].filter(Boolean).join(" · ");
    } else {
      step3Status = "ok";
      step3Detail = `Flood ${risk.flood_zone} · Wetlands ${risk.wetlands_percent.toFixed(0)}% · Tornado ${risk.tornado_risk}`;
    }
  }
  const step3: Step = {
    number: 3, label: "Risco Natural", sublabel: "Natureza contra?",
    icon: "🌊", status: step3Status, detail: step3Detail,
  };

  // ── Passo 4: Valuação ─────────────────────────────────────────────────────
  let step4Status: StepStatus = "pending";
  let step4Detail = "Valor de mercado não estimado";
  if (score?.market_value_estimate) {
    const disc = score.discount_percent ?? 0;
    if (disc >= 60) {
      step4Status = "ok";
      step4Detail = `Desconto de ${disc.toFixed(0)}% sobre o valor de mercado (excelente)`;
    } else if (disc >= 30) {
      step4Status = "warning";
      step4Detail = `Desconto de ${disc.toFixed(0)}% — margem moderada`;
    } else {
      step4Status = "warning";
      step4Detail = `Desconto de ${disc.toFixed(0)}% — margem baixa, requer análise`;
    }
    step4Detail += ` · Mercado estimado $${(score.market_value_estimate).toLocaleString("en-US")}`;
  }
  const step4: Step = {
    number: 4, label: "Valuação", sublabel: "Vale o preço pedido?",
    icon: "💰", status: step4Status, detail: step4Detail,
  };

  // ── Passo 5: Mercado ──────────────────────────────────────────────────────
  let step5Status: StepStatus = "pending";
  let step5Detail = "Dados demográficos não carregados";
  if (score?.score_population_growth != null) {
    const pts = score.score_population_growth;
    if (pts >= 15) {
      step5Status = "ok";
      step5Detail = "Crescimento populacional forte (≥5% em 3 anos)";
    } else if (pts >= 5) {
      step5Status = "warning";
      step5Detail = "Crescimento leve — mercado estável";
    } else {
      step5Status = "warning";
      step5Detail = "Sem crescimento detectado — mercado estagnado";
    }
  }
  const step5: Step = {
    number: 5, label: "Mercado", sublabel: "Região em crescimento?",
    icon: "📊", status: step5Status, detail: step5Detail,
  };

  // ── Passo 6: Cartório (Liens) ─────────────────────────────────────────────
  let step6Status: StepStatus = "pending";
  let step6Detail = "Clerk's Office não pesquisado";
  if (liens) {
    if (liens.surviving > 0) {
      step6Status = "fail";
      const typeLabels = liens.surviving_types
        .map((t) => LIEN_TYPE_LABELS[t] || t)
        .join(", ");
      step6Detail = `${liens.surviving} lien(s) sobrevivem ao tax deed: ${typeLabels} · Total: $${liens.surviving_amount.toLocaleString("en-US")}`;
    } else if (liens.active > 0) {
      step6Status = "warning";
      step6Detail = `${liens.active} lien(s) ativos, nenhum sobrevive ao tax deed · Serão extintos na venda`;
    } else if (liens.total === 0 && liens.records.length === 0) {
      step6Status = "pending";
      step6Detail = "Cartório não pesquisado (sem coordenador configurado)";
    } else {
      step6Status = "ok";
      step6Detail = `Nenhum lien pendente encontrado · ${liens.total} documento(s) verificado(s)`;
    }
  } else if (risk?.has_additional_liens) {
    step6Status = "fail";
    step6Detail = `Liens sobreviventes: $${(risk.liens_amount ?? 0).toLocaleString("en-US")} · Detalhe não disponível`;
  }
  const step6: Step = {
    number: 6, label: "Cartório", sublabel: "Liens sobrevivem ao deed?",
    icon: "📋", status: step6Status, detail: step6Detail,
  };

  // ── Passo 7: Decisão Final ────────────────────────────────────────────────
  let step7Status: StepStatus = "pending";
  let step7Detail = "Análise ainda não realizada";
  if (score) {
    const total = score.score_total ?? 0;
    const rec = score.ai_recommendation;
    const roi = score.of_roi_percent;
    if (rec === "comprar" || total >= 75) {
      step7Status = "ok";
    } else if (rec === "ignorar" || total < 30) {
      step7Status = "fail";
    } else {
      step7Status = "warning";
    }
    step7Detail = [
      `Score ${total}/100`,
      roi != null ? `ROI OF ${roi.toFixed(0)}%` : null,
      rec ? `IA: ${rec.toUpperCase()}` : "Sem análise IA",
    ].filter(Boolean).join(" · ");
  }
  const step7: Step = {
    number: 7, label: "Decisão", sublabel: "Comprar ou passar?",
    icon: "🤖", status: step7Status, detail: step7Detail,
  };

  return [step1, step2, step3, step4, step5, step6, step7];
}

interface Props {
  parcel: Parcel;
  liens: LiensResponse | null;
}

export default function DeedHunterSteps({ parcel, liens }: Props) {
  const steps = buildSteps(parcel, liens);
  const passedCount = steps.filter((s) => s.status === "ok").length;
  const failCount = steps.filter((s) => s.status === "fail").length;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="font-semibold text-gray-900">7 Passos do Método Deed Hunter</h3>
          <p className="text-xs text-gray-500 mt-0.5">Due diligence completa — cada passo deve estar verde antes de comprar</p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="px-2 py-0.5 bg-green-50 text-green-700 rounded-full font-medium">{passedCount} ok</span>
          {failCount > 0 && (
            <span className="px-2 py-0.5 bg-red-50 text-red-700 rounded-full font-medium">{failCount} falha</span>
          )}
        </div>
      </div>

      {/* Steps — horizontal timeline on desktop, vertical on mobile */}
      <div className="relative">
        {/* Connector line (desktop) */}
        <div className="hidden md:block absolute top-6 left-0 right-0 h-0.5 bg-gray-100 z-0" />

        <div className="grid grid-cols-1 md:grid-cols-7 gap-3 md:gap-1 relative z-10">
          {steps.map((step, _idx) => {
            const styles = STATUS_STYLES[step.status];
            return (
              <div key={step.number} className="flex md:flex-col items-start md:items-center gap-3 md:gap-2">
                {/* Step number circle */}
                <div className={`relative flex-shrink-0 w-12 h-12 rounded-full ${styles.bg} ring-4 ${styles.ring} flex items-center justify-center shadow-sm`}>
                  <span className="text-lg">{step.icon}</span>
                  <span className={`absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-white border-2 ${
                    step.status === "ok" ? "border-green-400" :
                    step.status === "fail" ? "border-red-400" :
                    step.status === "warning" ? "border-yellow-400" : "border-gray-300"
                  } flex items-center justify-center text-xs font-bold ${styles.text}`}>
                    {styles.icon}
                  </span>
                </div>

                {/* Step label */}
                <div className="md:text-center flex-1 md:flex-none">
                  <div className="text-xs text-gray-400 font-medium">Passo {step.number}</div>
                  <div className="text-sm font-semibold text-gray-900 leading-tight">{step.label}</div>
                  <div className="text-xs text-gray-500 leading-tight">{step.sublabel}</div>

                  {/* Detail tooltip — visible on mobile, tooltip on desktop */}
                  <div className={`mt-1 text-xs leading-tight ${styles.text} md:hidden`}>
                    {step.detail}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Detail rows — desktop only (below the timeline) */}
        <div className="hidden md:grid grid-cols-7 gap-1 mt-3">
          {steps.map((step) => {
            const styles = STATUS_STYLES[step.status];
            return (
              <div key={step.number} className={`text-xs text-center px-1 leading-tight ${styles.text}`} title={step.detail}>
                <div className="line-clamp-2">{step.detail}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
