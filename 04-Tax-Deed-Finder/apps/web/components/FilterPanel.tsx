"use client";
import { useState, useEffect } from "react";
import { fetchCounties, type County, type FilterParams } from "@/lib/api";
import { ChevronDown, ChevronUp } from "lucide-react";

interface Props {
  filters: FilterParams;
  onChange: (f: FilterParams) => void;
}

const STATES = ["TX", "GA", "TN", "AR", "FL", "NC"];

const inputCls = "w-full text-sm bg-bg-secondary border border-[rgba(201,145,10,0.30)] rounded px-3 py-2 text-parchment placeholder-parchment-dim focus:outline-none focus:border-[rgba(201,145,10,0.45)] transition-colors font-ibm";
const labelCls = "block text-[10px] uppercase tracking-widest text-parchment-dim font-ibm mb-1";

export default function FilterPanel({ filters, onChange }: Props) {
  const [counties, setCounties] = useState<County[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    fetchCounties().then(setCounties).catch(() => {});
  }, []);

  const filtered_counties = filters.state
    ? counties.filter((c) => c.state === filters.state)
    : counties;

  function set(key: keyof FilterParams, val: unknown) {
    onChange({ ...filters, [key]: val || undefined, page: 1 });
  }

  return (
    <div className="bg-bg-card border border-[rgba(201,145,10,0.30)] rounded-lg mb-6">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-4 text-sm font-ibm text-parchment-muted hover:text-parchment transition-colors"
      >
        <span className="text-[10px] uppercase tracking-widest">Filtros avançados</span>
        {open ? <ChevronUp size={14} strokeWidth={1.5} /> : <ChevronDown size={14} strokeWidth={1.5} />}
      </button>

      {open && (
        <div className="px-5 pb-5 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 border-t border-[rgba(201,145,10,0.10)] pt-4">
          <div>
            <label className={labelCls}>Tipo de imóvel</label>
            <select className={inputCls} value={filters.property_type || ""} onChange={(e) => set("property_type", e.target.value)}>
              <option value="">Todos</option>
              <option value="land">Terreno</option>
              <option value="house">Casa</option>
              <option value="commercial">Comercial</option>
            </select>
          </div>

          <div>
            <label className={labelCls}>Estado</label>
            <select className={inputCls} value={filters.state || ""} onChange={(e) => set("state", e.target.value)}>
              <option value="">Todos</option>
              {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          <div>
            <label className={labelCls}>Condado</label>
            <select className={inputCls} value={filters.county_id || ""} onChange={(e) => set("county_id", e.target.value)}>
              <option value="">Todos</option>
              {filtered_counties.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className={labelCls}>Score mínimo: {filters.min_score ?? 0}</label>
            <input
              type="range" min={0} max={100} step={5}
              value={filters.min_score ?? 0}
              onChange={(e) => set("min_score", Number(e.target.value))}
              className="w-full accent-gold-bright"
            />
          </div>

          <div>
            <label className={labelCls}>Lance mínimo ($)</label>
            <input type="number" placeholder="0" className={inputCls} value={filters.min_bid ?? ""} onChange={(e) => set("min_bid", Number(e.target.value) || undefined)} />
          </div>

          <div>
            <label className={labelCls}>Lance máximo ($)</label>
            <input type="number" placeholder="Sem limite" className={inputCls} value={filters.max_bid ?? ""} onChange={(e) => set("max_bid", Number(e.target.value) || undefined)} />
          </div>

          <div>
            <label className={labelCls}>Mín acres</label>
            <input type="number" placeholder="0" step="0.1" className={inputCls} value={filters.min_acres ?? ""} onChange={(e) => set("min_acres", Number(e.target.value) || undefined)} />
          </div>

          <div>
            <label className={labelCls}>Acesso</label>
            <select className={inputCls} value={filters.road_type || ""} onChange={(e) => set("road_type", e.target.value)}>
              <option value="">Qualquer</option>
              <option value="paved">Pavimentada</option>
              <option value="unpaved">Não pavimentada</option>
            </select>
          </div>

          <div>
            <label className={labelCls}>Distância máxima</label>
            <select className={inputCls} value={filters.max_drive_time ?? ""} onChange={(e) => set("max_drive_time", Number(e.target.value) || undefined)}>
              <option value="">Qualquer</option>
              <option value="30">30 min</option>
              <option value="60">60 min</option>
              <option value="90">90 min</option>
              <option value="120">120 min</option>
            </select>
          </div>

          <div>
            <label className={labelCls}>Desconto mínimo (%)</label>
            <input type="number" placeholder="0" min={0} max={100} className={inputCls} value={filters.min_discount ?? ""} onChange={(e) => set("min_discount", Number(e.target.value) || undefined)} />
          </div>

          <div>
            <label className={labelCls}>ROI mínimo (%)</label>
            <input type="number" placeholder="0" className={inputCls} value={filters.min_roi ?? ""} onChange={(e) => set("min_roi", Number(e.target.value) || undefined)} />
          </div>

          <div className="flex items-center gap-2 pt-5">
            <input
              type="checkbox" id="ai_filter"
              checked={!!filters.has_ai_analysis}
              onChange={(e) => set("has_ai_analysis", e.target.checked ? true : undefined)}
              className="accent-gold-bright"
            />
            <label htmlFor="ai_filter" className="text-xs text-parchment-muted font-ibm">Apenas com análise IA</label>
          </div>

          <div>
            <label className={labelCls}>Ordenar por</label>
            <select
              className={inputCls}
              value={`${filters.order_by ?? "score_total"}_${filters.order_dir ?? "desc"}`}
              onChange={(e) => {
                const val = e.target.value;
                const sep = val.lastIndexOf("_");
                onChange({ ...filters, order_by: val.slice(0, sep), order_dir: val.slice(sep + 1), page: 1 });
              }}
            >
              <option value="score_total_desc">Score (maior)</option>
              <option value="discount_percent_desc">Desconto % (maior)</option>
              <option value="minimum_bid_asc">Lance (menor)</option>
              <option value="auction_date_asc">Data leilão (próximo)</option>
              <option value="of_roi_percent_desc">ROI owner financing (maior)</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={() => onChange({ min_score: 0, order_by: "score_total", order_dir: "desc", page: 1 })}
              className="text-xs text-parchment-muted hover:text-gold-bright transition-colors font-ibm"
            >
              Limpar filtros
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
