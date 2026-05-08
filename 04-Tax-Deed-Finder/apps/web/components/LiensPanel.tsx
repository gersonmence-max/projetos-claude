"use client";
import type { LiensResponse } from "@/lib/api";
import { formatCurrency } from "@/lib/api";

const LIEN_TYPE_LABELS: Record<string, { label: string; color: string }> = {
  irs_federal:      { label: "IRS Federal",       color: "bg-red-100 text-red-800 border-red-200" },
  state_tax:        { label: "Imposto Estadual",   color: "bg-orange-100 text-orange-800 border-orange-200" },
  hoa:              { label: "HOA",                color: "bg-purple-100 text-purple-800 border-purple-200" },
  hospital:         { label: "Hospitalar",         color: "bg-blue-100 text-blue-800 border-blue-200" },
  code_enforcement: { label: "Código Municipal",   color: "bg-yellow-100 text-yellow-800 border-yellow-200" },
  judgment:         { label: "Judicial",           color: "bg-pink-100 text-pink-800 border-pink-200" },
  mechanics:        { label: "Empreiteiro",        color: "bg-indigo-100 text-indigo-800 border-indigo-200" },
  other:            { label: "Outro",              color: "bg-gray-100 text-gray-700 border-gray-200" },
};

interface Props {
  liens: LiensResponse;
  clerkUrl?: string;
}

export default function LiensPanel({ liens, clerkUrl }: Props) {
  if (liens.total === 0) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-xl p-5">
        <div className="flex items-center gap-2">
          <span className="text-green-600 text-xl">✓</span>
          <div>
            <div className="font-semibold text-green-800">Nenhum lien encontrado</div>
            <div className="text-sm text-green-700">Cartório pesquisado — sem pendências registradas</div>
          </div>
        </div>
        {clerkUrl && (
          <a href={clerkUrl} target="_blank" rel="noopener noreferrer"
            className="text-xs text-green-600 hover:underline mt-2 block">
            Verificar manualmente no portal do cartório ↗
          </a>
        )}
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-900">Ônus — Clerk&apos;s Office</h3>
        <div className="flex gap-2 text-xs">
          {liens.surviving > 0 && (
            <span className="px-2 py-1 bg-red-50 text-red-700 rounded-full font-semibold border border-red-200">
              ⚠ {liens.surviving} sobrevive(m) ao deed
            </span>
          )}
          <span className="px-2 py-1 bg-gray-50 text-gray-600 rounded-full border border-gray-200">
            {liens.active} ativo(s) de {liens.total} encontrado(s)
          </span>
        </div>
      </div>

      {/* Surviving liens warning */}
      {liens.surviving > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm">
          <div className="font-semibold text-red-800 mb-1">
            Atenção: {liens.surviving} lien(s) sobrevivem ao tax deed
          </div>
          <div className="text-red-700">
            Total a pagar pelo comprador: <strong>{formatCurrency(liens.surviving_amount)}</strong>
          </div>
          <div className="text-xs text-red-600 mt-1">
            Liens federais IRS nunca são extintos pela venda de tax deed (26 U.S.C. §7425).
            Adicione esse valor ao custo total da aquisição.
          </div>
        </div>
      )}

      {/* Liens table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-xs text-gray-500 uppercase">
              <th className="text-left py-2 pr-3">Tipo</th>
              <th className="text-left py-2 pr-3">Credor</th>
              <th className="text-right py-2 pr-3">Valor</th>
              <th className="text-left py-2 pr-3">Registrado</th>
              <th className="text-center py-2 pr-3">Quitado</th>
              <th className="text-center py-2">Sobrevive</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {liens.records.map((r, i) => {
              const typeInfo = LIEN_TYPE_LABELS[r.lien_type] || LIEN_TYPE_LABELS.other;
              return (
                <tr key={r.id || i} className={r.survives_tax_deed && !r.is_released ? "bg-red-50/30" : ""}>
                  <td className="py-2 pr-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${typeInfo.color}`}>
                      {typeInfo.label}
                    </span>
                  </td>
                  <td className="py-2 pr-3 text-gray-700 max-w-[160px] truncate" title={r.grantee || ""}>
                    {r.grantee || "—"}
                  </td>
                  <td className="py-2 pr-3 text-right font-medium">
                    {r.lien_amount != null ? formatCurrency(r.lien_amount) : "—"}
                  </td>
                  <td className="py-2 pr-3 text-gray-500 text-xs">
                    {r.recorded_date ? new Date(r.recorded_date).toLocaleDateString("pt-BR") : "—"}
                  </td>
                  <td className="py-2 pr-3 text-center">
                    {r.is_released ? (
                      <span className="text-green-600 font-semibold text-xs">✓ Sim</span>
                    ) : (
                      <span className="text-red-500 text-xs">Não</span>
                    )}
                  </td>
                  <td className="py-2 text-center">
                    {r.survives_tax_deed ? (
                      <span className="text-red-600 font-semibold text-xs" title={r.survive_reason || ""}>
                        ⚠ Sim
                      </span>
                    ) : (
                      <span className="text-green-600 text-xs">Não</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {clerkUrl && (
        <a href={clerkUrl} target="_blank" rel="noopener noreferrer"
          className="text-xs text-blue-600 hover:underline mt-3 block">
          Verificar manualmente no portal do cartório ↗
        </a>
      )}
    </div>
  );
}
