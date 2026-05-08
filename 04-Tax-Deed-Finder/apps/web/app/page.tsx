"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { fetchSummary, fetchParcels, formatCurrency } from "@/lib/api";
import ScoreBadge from "@/components/ScoreBadge";
import { Map, TrendingUp, Award, Clock, ExternalLink, Star } from "lucide-react";

function SummaryCard({
  label,
  value,
  sub,
  Icon,
}: {
  label: string;
  value: string | number;
  sub?: string;
  Icon: React.ElementType;
}) {
  return (
    <div className="relative bg-bg-card border border-[rgba(201,145,10,0.30)] border-t-2 border-t-gold-bright rounded-lg p-5 shadow-card-inset hover:border-[rgba(201,145,10,0.60)] hover:shadow-gold transition-all duration-200 group">
      <div className="absolute top-4 right-4 opacity-60">
        <Icon size={16} strokeWidth={1.5} className="text-gold" />
      </div>
      <div className="text-[11px] uppercase tracking-widest text-parchment-muted font-ibm">{label}</div>
      <div className="text-3xl font-mono text-parchment font-medium mt-2">{value}</div>
      {sub && <div className="text-[11px] text-parchment-muted mt-1">{sub}</div>}
    </div>
  );
}

function auctionUrgencyClass(dateStr: string | null): string {
  if (!dateStr) return "text-parchment-muted";
  const diff = Math.ceil((new Date(dateStr).getTime() - Date.now()) / 86400000);
  if (diff <= 1) return "text-danger font-medium";
  if (diff <= 7) return "text-gold-bright";
  return "text-parchment-muted";
}

export default function HomePage() {
  const { data: summary } = useQuery({
    queryKey: ["summary"],
    queryFn: fetchSummary,
  });

  const { data: hotOpps, isLoading: loadingHot } = useQuery({
    queryKey: ["hot-opps"],
    queryFn: () => fetchParcels({ min_score: 75, order_by: "score_total", order_dir: "desc", page_size: 10 }),
  });

  const { data: soon } = useQuery({
    queryKey: ["soon"],
    queryFn: () => fetchParcels({ order_by: "auction_date", order_dir: "asc", page_size: 5 }),
  });

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-cinzel font-semibold text-parchment">Dashboard</h1>
          <p className="text-sm text-parchment-muted mt-1 font-ibm">Monitoramento de tax deed nos EUA</p>
        </div>
        <div className="flex items-center gap-2 border border-[rgba(201,145,10,0.40)] rounded-full px-3 py-1">
          <span className="w-1.5 h-1.5 rounded-full bg-gold-bright animate-pulse" />
          <span className="text-gold-bright text-[10px] font-ibm uppercase tracking-widest">Expedição Ativa</span>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <SummaryCard label="Total monitorado" value={summary?.total_monitored ?? "—"} Icon={Map} />
        <SummaryCard label="Novos hoje" value={summary?.new_today ?? "—"} Icon={TrendingUp} />
        <SummaryCard label="Score 70+" value={summary?.score_70_plus ?? "—"} sub="Alta qualidade" Icon={Award} />
        <SummaryCard label="Leilões em 7 dias" value={summary?.auctions_next_7_days ?? "—"} sub="Atenção urgente" Icon={Clock} />
      </div>

      {/* Hot opportunities table */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-cinzel text-parchment">Oportunidades quentes (score &ge; 75)</h2>
          <Link href="/imoveis?min_score=75" className="text-xs text-gold hover:text-gold-bright transition-colors">
            Ver todos &rarr;
          </Link>
        </div>
        <div className="bg-bg-card border border-[rgba(201,145,10,0.30)] rounded-lg overflow-hidden">
          {loadingHot ? (
            <div className="p-8 space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="skeleton h-8 rounded" />
              ))}
            </div>
          ) : !hotOpps?.items.length ? (
            <div className="bg-bg-card border border-[rgba(201,145,10,0.25)] rounded-lg p-12 text-center">
              <div className="flex flex-col items-center gap-3">
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-parchment-dim"><circle cx="12" cy="12" r="10"/><path d="M16.2 7.8l-2 6.3-6.4 2.1 2-6.3z"/></svg>
                <span className="font-cinzel text-parchment-dim text-sm">Nenhuma propriedade encontrada</span>
                <span className="text-xs text-parchment-dim/60">Ajuste os filtros ou aguarde a próxima coleta</span>
              </div>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-bg-secondary border-b border-[rgba(201,145,10,0.15)]">
                  <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest text-parchment-dim font-ibm">Score</th>
                  <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest text-parchment-dim font-ibm">Endereço</th>
                  <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest text-parchment-dim font-ibm">Município</th>
                  <th className="px-4 py-3 text-right text-[10px] uppercase tracking-widest text-parchment-dim font-ibm">Valor Est.</th>
                  <th className="px-4 py-3 text-right text-[10px] uppercase tracking-widest text-parchment-dim font-ibm">Desconto</th>
                  <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest text-parchment-dim font-ibm">Data Leilão</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {hotOpps.items.map((p) => (
                  <tr
                    key={p.id}
                    className="border-b border-[rgba(201,145,10,0.10)] hover:bg-gold/5 hover:border-l-2 hover:border-l-gold-bright transition-all duration-150 group"
                  >
                    <td className="px-4 py-3">
                      <ScoreBadge score={p.parcel_scores?.score_total} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm font-ibm text-parchment font-medium truncate max-w-xs">{p.address || "—"}</div>
                      {p.parcel_number && <div className="text-xs text-parchment-muted">APN: {p.parcel_number}</div>}
                    </td>
                    <td className="px-4 py-3 text-xs text-parchment-muted">
                      {p.counties?.name}, {p.state}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-parchment text-sm">
                      {formatCurrency(p.parcel_scores?.market_value_estimate)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-gold-bright text-sm">
                      {p.parcel_scores?.discount_percent != null
                        ? `${p.parcel_scores.discount_percent.toFixed(0)}%`
                        : "—"}
                    </td>
                    <td className={`px-4 py-3 text-sm ${auctionUrgencyClass(p.auction_date)}`}>
                      {p.auction_date ? new Date(p.auction_date).toLocaleDateString("pt-BR") : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button className="text-parchment-muted hover:text-gold-bright transition-colors">
                          <Star size={16} strokeWidth={1.5} />
                        </button>
                        <Link href={`/imoveis/${p.id}`} className="text-parchment-muted hover:text-gold-bright transition-colors">
                          <ExternalLink size={16} strokeWidth={1.5} />
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Próximos leilões em 48h */}
      <div>
        <h2 className="text-base font-cinzel text-parchment mb-3">Próximos leilões em 48h</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {(soon?.items || [])
            .filter((p) => {
              if (!p.auction_date) return false;
              const days = Math.ceil((new Date(p.auction_date).getTime() - Date.now()) / 86400000);
              return days >= 0 && days <= 2;
            })
            .map((p) => (
              <Link
                key={p.id}
                href={`/imoveis/${p.id}`}
                className="bg-bg-card border border-[rgba(201,145,10,0.30)] rounded-lg p-4 hover:border-[rgba(201,145,10,0.60)] hover:shadow-gold transition-all duration-200"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-ibm uppercase tracking-widest text-danger border border-danger/40 px-2 py-0.5 rounded-full">
                    Urgente
                  </span>
                  <ScoreBadge score={p.parcel_scores?.score_total} />
                </div>
                <div className="font-cinzel text-sm text-parchment truncate mt-2">{p.address || "—"}</div>
                <div className="text-xs text-parchment-muted mt-1">{p.counties?.name}, {p.state}</div>
                <div className="font-mono text-parchment text-sm font-medium mt-2">{formatCurrency(p.minimum_bid)}</div>
                <div className="text-xs text-danger mt-1">
                  Leilão: {p.auction_date ? new Date(p.auction_date).toLocaleDateString("pt-BR") : "—"}
                </div>
              </Link>
            ))}
          {!soon?.items.filter((p) => {
            if (!p.auction_date) return false;
            const days = Math.ceil((new Date(p.auction_date).getTime() - Date.now()) / 86400000);
            return days >= 0 && days <= 2;
          }).length && (
            <div className="col-span-3 text-center text-parchment-muted text-sm py-6 font-ibm">
              Nenhum leilão nos próximos 2 dias.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
