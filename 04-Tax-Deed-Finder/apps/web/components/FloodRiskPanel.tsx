"use client";
import type { ParcelRisk } from "@/lib/api";

const FLOOD_ZONE_INFO: Record<string, { label: string; period: string; color: string; description: string }> = {
  X:    { label: "Zona X — Risco mínimo",        period: "Fora da área de 500 anos", color: "bg-green-50 border-green-200 text-green-800",  description: "Área fora da planície de inundação de 500 anos. Risco muito baixo." },
  X500: { label: "Zona X (500 anos)",             period: "Inundação a cada 500 anos",color: "bg-yellow-50 border-yellow-200 text-yellow-800",description: "0,2% de chance de inundação por ano. Risco moderado." },
  A:    { label: "Zona A — Alto risco",           period: "Inundação a cada 100 anos", color: "bg-red-50 border-red-200 text-red-800",        description: "1% de chance de inundação por ano. Seguro obrigatório para financiamentos." },
  AE:   { label: "Zona AE — Alto risco",          period: "Inundação a cada 100 anos", color: "bg-red-50 border-red-200 text-red-800",        description: "1% de chance de inundação por ano. Elevação base determinada pelo FEMA." },
  AH:   { label: "Zona AH — Alagamento raso",     period: "Inundação a cada 100 anos", color: "bg-red-50 border-red-200 text-red-800",        description: "Alagamento de 1 a 3 pés de profundidade. Comum em planícies." },
  AO:   { label: "Zona AO — Fluxo em lençol",     period: "Inundação a cada 100 anos", color: "bg-red-50 border-red-200 text-red-800",        description: "Fluxo de água superficial sobre encostas ou planícies." },
  VE:   { label: "Zona VE — Risco costeiro",      period: "Inundação a cada 100 anos", color: "bg-red-50 border-red-200 text-red-900 font-bold", description: "Zona costeira de alto risco com ondas. Risco extremo." },
  V:    { label: "Zona V — Risco costeiro",       period: "Inundação a cada 100 anos", color: "bg-red-50 border-red-200 text-red-900 font-bold", description: "Zona costeira de alto risco com ondas. Risco extremo." },
  D:    { label: "Zona D — Risco indeterminado",  period: "Não avaliado pelo FEMA",    color: "bg-gray-50 border-gray-200 text-gray-700",     description: "Área não mapeada pelo FEMA. Risco incerto." },
};

function getFloodInfo(zone: string) {
  const key = zone?.toUpperCase().replace(/\d+/g, "") || "X";
  return FLOOD_ZONE_INFO[zone?.toUpperCase()] ?? FLOOD_ZONE_INFO[key] ?? FLOOD_ZONE_INFO["X"];
}

function getReturnPeriodRisk(zone: string) {
  const z = zone?.toUpperCase() ?? "";
  if (["A","AE","AH","AO","VE","V","A99","AR","A1","A2","A3","A4","A5","A6","A7","A8","A9","A10","A11","A12","A13","A14","A15","A16","A17","A18","A19","A20","A21","A22","A23","A24","A25","A26","A27","A28","A29","A30"].includes(z)) {
    return "100";
  }
  if (z === "X500" || z.includes("500")) return "500";
  if (z === "X") return "none";
  return "unknown";
}

export default function FloodRiskPanel({ risk }: { risk: ParcelRisk }) {
  const info = getFloodInfo(risk.flood_zone ?? "X");
  const returnPeriod = getReturnPeriodRisk(risk.flood_zone ?? "X");

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="font-semibold text-gray-900 mb-4">Risco de Inundação e Wetlands</h3>

      {/* Flood zone principal */}
      <div className={`rounded-lg border p-4 mb-4 ${info.color}`}>
        <div className="flex items-start justify-between">
          <div>
            <div className="font-semibold text-sm">{info.label}</div>
            <div className="text-xs mt-1 opacity-80">{info.period}</div>
          </div>
          <span className="text-xs font-mono bg-white/60 px-2 py-1 rounded">{risk.flood_zone ?? "X"}</span>
        </div>
        <p className="text-xs mt-2 opacity-90">{info.description}</p>
      </div>

      {/* Tabela de períodos de retorno */}
      <div className="mb-4">
        <div className="text-xs font-semibold text-gray-500 uppercase mb-2">Probabilidade de inundação</div>
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: "1 ano",    pct: returnPeriod === "100" ? ">1%" : "<1%",         risk: returnPeriod === "100" },
            { label: "30 anos",  pct: returnPeriod === "100" ? "~26%" : "<1%",        risk: returnPeriod === "100" },
            { label: "50 anos",  pct: returnPeriod === "100" ? "~40%" : "<10%",       risk: returnPeriod === "100" },
            { label: "100 anos", pct: returnPeriod === "100" ? "~63%" : returnPeriod === "500" ? "~18%" : "<10%", risk: returnPeriod === "100" },
            { label: "500 anos", pct: returnPeriod === "none" ? "Mínima" : returnPeriod === "500" ? "~63%" : "~86%", risk: returnPeriod !== "none" },
            { label: "1.000 anos",pct: returnPeriod === "none" ? "Mínima" : "Possível", risk: false },
          ].map(({ label, pct, risk: isRisk }) => (
            <div key={label} className={`rounded-lg p-3 text-center border ${isRisk ? "bg-red-50 border-red-200" : "bg-gray-50 border-gray-200"}`}>
              <div className="text-xs text-gray-500">{label}</div>
              <div className={`text-sm font-semibold mt-1 ${isRisk ? "text-red-700" : "text-gray-600"}`}>{pct}</div>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-400 mt-2">
          Probabilidade acumulada de ao menos uma inundação no período. Fonte: FEMA NFHL.
        </p>
      </div>

      {/* Wetlands */}
      <div className="border-t border-gray-100 pt-4">
        <div className="text-xs font-semibold text-gray-500 uppercase mb-2">Wetlands (FWS)</div>
        <div className="flex items-center gap-3">
          <div className="flex-1 bg-gray-100 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${risk.wetlands_percent > 50 ? "bg-blue-600" : risk.wetlands_percent > 20 ? "bg-blue-400" : "bg-blue-200"}`}
              style={{ width: `${Math.min(risk.wetlands_percent ?? 0, 100)}%` }}
            />
          </div>
          <span className={`text-sm font-semibold ${risk.wetlands_percent > 50 ? "text-blue-700" : "text-gray-600"}`}>
            {(risk.wetlands_percent ?? 0).toFixed(0)}%
          </span>
        </div>
        <p className="text-xs text-gray-400 mt-1">
          {risk.wetlands_percent > 50
            ? "Mais da metade da área é wetland — imóvel descartado automaticamente."
            : risk.wetlands_percent > 20
            ? "Área parcialmente em wetlands — verifique usabilidade."
            : "Área com pouca ou nenhuma cobertura de wetlands."}
        </p>
      </div>
    </div>
  );
}
