"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchSaved, removeSaved, formatCurrency } from "@/lib/api";
import Link from "next/link";
import ScoreBadge from "@/components/ScoreBadge";
import { useState } from "react";
import { Trash2, ExternalLink } from "lucide-react";

export default function SalvosPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["saved"], queryFn: fetchSaved });
  const [_notes, setNotes] = useState<Record<string, string>>({});

  const remove = useMutation({
    mutationFn: removeSaved,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["saved"] }),
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-24 rounded-lg" />)}
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-cinzel font-semibold text-parchment mb-6">Imóveis Salvos</h1>

      {!data?.length ? (
        <div className="bg-bg-card border border-[rgba(201,145,10,0.25)] rounded-lg p-12 text-center">
          <div className="flex flex-col items-center gap-3">
            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-parchment-dim"><circle cx="12" cy="12" r="10"/><path d="M16.2 7.8l-2 6.3-6.4 2.1 2-6.3z"/></svg>
            <span className="font-cinzel text-parchment-dim text-sm">Nenhuma propriedade encontrada</span>
            <Link href="/imoveis" className="text-xs text-gold hover:text-gold-bright transition-colors font-ibm">
              Explorar imóveis &rarr;
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {data.map((s: { id: string; notes: string | null; saved_at: string; parcels: Record<string, unknown> }) => {
            const p = s.parcels as Record<string, unknown>;
            const score = (p?.parcel_scores as Record<string, unknown>);
            const county = (p?.counties as Record<string, unknown>);
            return (
              <div key={s.id} className="bg-bg-card border border-[rgba(201,145,10,0.30)] rounded-lg p-5 hover:border-[rgba(201,145,10,0.60)] transition-all">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <Link href={`/imoveis/${p?.id}`} className="font-cinzel text-parchment hover:text-gold-bright transition-colors text-sm">
                      {(p?.address as string) || "Sem endereço"}
                    </Link>
                    <p className="text-xs text-parchment-muted mt-1 font-ibm">
                      {county?.name as string}, {p?.state as string} &middot;{" "}
                      Lance: {formatCurrency(p?.minimum_bid as number)} &middot;{" "}
                      {p?.auction_date ? new Date(p.auction_date as string).toLocaleDateString("pt-BR") : "Data N/A"}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 ml-4 shrink-0">
                    <ScoreBadge score={score?.score_total as number} />
                    <Link href={`/imoveis/${p?.id}`} className="text-parchment-muted hover:text-gold-bright transition-colors">
                      <ExternalLink size={15} strokeWidth={1.5} />
                    </Link>
                    <button
                      onClick={() => remove.mutate(s.id)}
                      className="text-parchment-muted hover:text-danger transition-colors"
                    >
                      <Trash2 size={15} strokeWidth={1.5} />
                    </button>
                  </div>
                </div>
                <div className="mt-3">
                  <textarea
                    className="w-full text-xs bg-bg-secondary border border-[rgba(201,145,10,0.30)] rounded px-3 py-2 resize-none text-parchment placeholder-parchment-dim focus:outline-none focus:border-[rgba(201,145,10,0.60)] transition-colors font-ibm"
                    rows={2}
                    placeholder="Adicione notas sobre este imóvel..."
                    defaultValue={s.notes || ""}
                    onChange={(e) => setNotes((n) => ({ ...n, [s.id]: e.target.value }))}
                  />
                </div>
                <div className="text-[10px] text-parchment-dim mt-1 font-ibm">
                  Salvo em {new Date(s.saved_at).toLocaleDateString("pt-BR")}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
