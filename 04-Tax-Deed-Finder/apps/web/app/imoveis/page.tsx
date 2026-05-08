"use client";
import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchParcels, type FilterParams, type ParcelsResponse } from "@/lib/api";
import FilterPanel from "@/components/FilterPanel";
import ParcelTable from "@/components/ParcelTable";
import { Download } from "lucide-react";

const DEFAULT_FILTERS: FilterParams = {
  min_score: 0,
  order_by: "score_total",
  order_dir: "desc",
  page: 1,
  page_size: 50,
};

function exportCSV(items: unknown[]) {
  if (!items.length) return;
  const keys = Object.keys((items[0] as Record<string, unknown>)).filter((k) => typeof (items[0] as Record<string, unknown>)[k] !== "object");
  const csv = [keys.join(","), ...items.map((i) =>
    keys.map((k) => JSON.stringify((i as Record<string, unknown>)[k] ?? "")).join(",")
  )].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `landhq-${Date.now()}.csv`;
  a.click();
}

export default function ImoveisPage() {
  const [filters, setFilters] = useState<FilterParams>(DEFAULT_FILTERS);

  const { data, isLoading } = useQuery<ParcelsResponse>({
    queryKey: ["parcels", filters],
    queryFn: () => fetchParcels(filters),
    placeholderData: (prev) => prev,
  });

  const handleFilters = useCallback((f: FilterParams) => setFilters(f), []);
  const totalPages = data ? Math.ceil(data.total / (filters.page_size || 50)) : 1;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-cinzel font-semibold text-parchment">Imóveis</h1>
          <p className="text-sm text-parchment-muted mt-1 font-ibm">
            {data?.total ?? "—"} imóveis encontrados
          </p>
        </div>
        <button
          onClick={() => exportCSV(data?.items || [])}
          className="flex items-center gap-2 text-sm px-4 py-2 border border-[rgba(201,145,10,0.60)] text-gold bg-transparent hover:border-[rgba(201,145,10,0.70)] hover:text-gold-bright hover:bg-gold/5 rounded transition-all font-ibm"
        >
          <Download size={14} strokeWidth={1.5} />
          Exportar CSV
        </button>
      </div>

      <FilterPanel filters={filters} onChange={handleFilters} />
      <ParcelTable parcels={data?.items || []} loading={isLoading} />

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            disabled={!filters.page || filters.page <= 1}
            onClick={() => setFilters((f) => ({ ...f, page: (f.page || 1) - 1 }))}
            className="px-3 py-1.5 text-sm border border-[rgba(201,145,10,0.30)] text-parchment-muted rounded disabled:opacity-30 hover:border-[rgba(201,145,10,0.45)] hover:text-parchment transition-all font-ibm"
          >
            &larr; Anterior
          </button>
          <span className="text-sm text-parchment-muted font-mono">
            {filters.page || 1} / {totalPages}
          </span>
          <button
            disabled={(filters.page || 1) >= totalPages}
            onClick={() => setFilters((f) => ({ ...f, page: (f.page || 1) + 1 }))}
            className="px-3 py-1.5 text-sm border border-[rgba(201,145,10,0.30)] text-parchment-muted rounded disabled:opacity-30 hover:border-[rgba(201,145,10,0.45)] hover:text-parchment transition-all font-ibm"
          >
            Próxima &rarr;
          </button>
        </div>
      )}
    </div>
  );
}
