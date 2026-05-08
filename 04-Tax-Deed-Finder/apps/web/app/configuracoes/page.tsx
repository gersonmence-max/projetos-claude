"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchCounties, toggleCounty, triggerPipeline, type County } from "@/lib/api";
import { useState } from "react";
import { Play } from "lucide-react";

const PLATFORM_LABELS: Record<string, string> = {
  bid4assets: "Bid4Assets",
  govease: "GovEase",
  realauction: "RealAuction",
  direct: "Portal direto",
};

export default function ConfiguracoesPage() {
  const qc = useQueryClient();
  const { data: counties } = useQuery({ queryKey: ["counties"], queryFn: fetchCounties });
  const [pipelineStatus, setPipelineStatus] = useState<string>("");

  const toggle = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) => toggleCounty(id, active),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["counties"] }),
  });

  async function handleRunPipeline() {
    setPipelineStatus("iniciando...");
    try {
      await triggerPipeline();
      setPipelineStatus("Pipeline iniciado! Verifique o dashboard em ~30 minutos.");
    } catch {
      setPipelineStatus("Erro ao iniciar pipeline. Verifique as credenciais.");
    }
  }

  const byState = (counties || []).reduce<Record<string, County[]>>((acc, c) => {
    acc[c.state] = [...(acc[c.state] || []), c];
    return acc;
  }, {});

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-cinzel font-semibold text-parchment mb-6">Configurações</h1>

      {/* Pipeline control */}
      <div className="bg-bg-card border border-[rgba(201,145,10,0.30)] rounded-lg p-5 mb-6 shadow-card-inset">
        <h2 className="font-cinzel text-parchment mb-1">Pipeline de coleta</h2>
        <p className="text-xs text-parchment-muted mb-4 font-ibm">
          O pipeline roda automaticamente toda madrugada às 2h. Você pode acionar manualmente aqui.
        </p>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRunPipeline}
            className="flex items-center gap-2 px-4 py-2 bg-gold text-bg-primary text-sm font-ibm font-medium rounded hover:bg-gold-bright transition-colors"
          >
            <Play size={14} strokeWidth={1.5} />
            Executar pipeline agora
          </button>
          {pipelineStatus && (
            <span className="text-xs text-parchment-muted font-ibm">{pipelineStatus}</span>
          )}
        </div>
      </div>

      {/* County management */}
      <div className="bg-bg-card border border-[rgba(201,145,10,0.30)] rounded-lg p-5 mb-6">
        <h2 className="font-cinzel text-parchment mb-1">Condados monitorados</h2>
        <p className="text-xs text-parchment-muted mb-4 font-ibm">
          Desative condados para excluí-los da próxima coleta.
        </p>

        <div className="space-y-6">
          {Object.entries(byState).sort().map(([state, list]) => (
            <div key={state}>
              <h3 className="text-[10px] font-ibm uppercase tracking-widest text-parchment-dim mb-2">{state}</h3>
              <div className="divide-y divide-[rgba(201,145,10,0.08)]">
                {list.map((county) => (
                  <div key={county.id} className="flex items-center justify-between py-2.5">
                    <div>
                      <span className="text-sm font-ibm text-parchment">{county.name}</span>
                      <span className="ml-2 text-[10px] uppercase tracking-wide text-parchment-dim">
                        {PLATFORM_LABELS[county.auction_platform] || county.auction_platform}
                      </span>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={county.active}
                        onChange={(e) => toggle.mutate({ id: county.id, active: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-bg-secondary border border-[rgba(201,145,10,0.30)] rounded-full peer peer-checked:bg-gold peer-checked:border-gold after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-parchment-dim after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-full peer-checked:after:bg-bg-primary" />
                    </label>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* System info */}
      <div className="bg-bg-card border border-[rgba(201,145,10,0.30)] rounded-lg p-5">
        <h2 className="font-cinzel text-parchment mb-3">Informações do sistema</h2>
        <dl className="space-y-2">
          {[
            ["Condados ativos", counties?.filter((c) => c.active).length ?? "—"],
            ["Condados inativos", counties?.filter((c) => !c.active).length ?? "—"],
            ["Score mínimo para Rentcast", "50"],
            ["Score mínimo para análise IA", "70"],
            ["Score mínimo para alerta email", "75"],
            ["Modelo IA", "claude-sonnet-4-20250514"],
          ].map(([k, v]) => (
            <div key={k} className="flex justify-between text-sm border-b border-[rgba(201,145,10,0.08)] pb-2 last:border-0 last:pb-0">
              <dt className="text-parchment-muted font-ibm">{k}</dt>
              <dd className="font-mono text-parchment">{v}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
