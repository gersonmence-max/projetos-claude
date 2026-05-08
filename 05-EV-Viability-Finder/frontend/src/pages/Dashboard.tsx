import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { RefreshCw } from "lucide-react";
import type { Property, PropertyFilters } from "../types";
import { fetchProperties } from "../api/properties";
import FilterPanel from "../components/FilterPanel";
import PropertyTable from "../components/PropertyTable";

export default function Dashboard() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [filters, setFilters] = useState<PropertyFilters>({});
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const load = async (f: PropertyFilters) => {
    setIsLoading(true);
    try {
      const data = await fetchProperties(f);
      setProperties(data);
      setLastUpdated(new Date());
    } catch (err) {
      console.error("Erro ao carregar propriedades:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load(filters);
  }, [filters]);

  const forte = properties.filter((p) => p.classification === "FORTE").length;
  const moderado = properties.filter((p) => p.classification === "MODERADO").length;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "#e2e8f0" }}>
            Terrenos
          </h1>
          <p className="text-sm mt-1" style={{ color: "#64748b" }}>
            {properties.length} propriedades encontradas
            {lastUpdated && (
              <span className="ml-2 opacity-60">
                · atualizado às {lastUpdated.toLocaleTimeString("pt-BR")}
              </span>
            )}
          </p>
        </div>

        <button
          onClick={() => load(filters)}
          disabled={isLoading}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all disabled:opacity-40"
          style={{
            backgroundColor: "#12121a",
            border: "1px solid #1e1e2e",
            color: "#64748b",
          }}
        >
          <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} />
          Atualizar
        </button>
      </motion.div>

      {/* Stats */}
      {!isLoading && properties.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-3 gap-4"
        >
          {[
            { label: "Total", value: properties.length, color: "#e2e8f0" },
            { label: "FORTE", value: forte, color: "#22c55e" },
            { label: "MODERADO", value: moderado, color: "#f59e0b" },
          ].map(({ label, value, color }) => (
            <div
              key={label}
              className="rounded-xl p-4"
              style={{ backgroundColor: "#12121a", border: "1px solid #1e1e2e" }}
            >
              <p className="text-xs mb-1" style={{ color: "#64748b" }}>
                {label}
              </p>
              <p className="text-2xl font-bold font-mono" style={{ color }}>
                {value}
              </p>
            </div>
          ))}
        </motion.div>
      )}

      {/* Filters */}
      <FilterPanel filters={filters} onChange={setFilters} />

      {/* Table */}
      <PropertyTable data={properties} isLoading={isLoading} />
    </div>
  );
}
