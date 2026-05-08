import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  MapPin,
  Maximize2,
  DollarSign,
  TrendingDown,
  Shield,
  ExternalLink,
  Map,
  Eye,
  Calendar,
} from "lucide-react";
import type { Property } from "../types";
import { fetchProperty } from "../api/properties";
import ScoreBadge from "../components/ScoreBadge";
import {
  formatCurrency,
  formatAcres,
  formatDiscount,
  formatSaleDate,
  buildGoogleMapsUrl,
  buildStreetViewUrl,
} from "../lib/utils";

function DataRow({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div
      className="flex items-center gap-3 py-3"
      style={{ borderBottom: "1px solid rgba(30,30,46,0.5)" }}
    >
      <Icon size={16} style={{ color: "#64748b" }} className="flex-shrink-0" />
      <span className="text-sm flex-1" style={{ color: "#64748b" }}>
        {label}
      </span>
      <span className="text-sm font-medium text-right" style={{ color: "#e2e8f0" }}>
        {value}
      </span>
    </div>
  );
}

function ActionButton({
  href,
  icon: Icon,
  label,
  primary,
}: {
  href: string;
  icon: React.ElementType;
  label: string;
  primary?: boolean;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm transition-all"
      style={
        primary
          ? { backgroundColor: "#6c63ff", color: "#ffffff" }
          : {
              backgroundColor: "#12121a",
              border: "1px solid #1e1e2e",
              color: "#e2e8f0",
            }
      }
      onMouseEnter={(e) => {
        if (primary) e.currentTarget.style.backgroundColor = "#5a52e0";
        else e.currentTarget.style.borderColor = "rgba(108,99,255,0.5)";
      }}
      onMouseLeave={(e) => {
        if (primary) e.currentTarget.style.backgroundColor = "#6c63ff";
        else e.currentTarget.style.borderColor = "#1e1e2e";
      }}
    >
      <Icon size={15} />
      {label}
    </a>
  );
}

const CLASSIFICATION_STYLE: Record<string, { bg: string; text: string }> = {
  FORTE:    { bg: "rgba(34,197,94,0.15)",  text: "#22c55e" },
  MODERADO: { bg: "rgba(251,191,36,0.15)", text: "#f59e0b" },
  FRACO:    { bg: "rgba(100,116,139,0.15)", text: "#64748b" },
  EVITAR:   { bg: "rgba(239,68,68,0.15)",  text: "#ef4444" },
};

function ClassificationBadge({ classification }: { classification: string | null }) {
  if (!classification) return null;
  const s = CLASSIFICATION_STYLE[classification] ?? { bg: "transparent", text: "#64748b" };
  return (
    <span
      className="px-3 py-1 rounded-full text-sm font-semibold"
      style={{ backgroundColor: s.bg, color: s.text }}
    >
      {classification}
    </span>
  );
}

export default function PropertyDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [property, setProperty] = useState<Property | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    fetchProperty(Number(id))
      .then(setProperty)
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, [id]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full py-24">
        <div
          className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin"
          style={{ borderColor: "#6c63ff", borderTopColor: "transparent" }}
        />
      </div>
    );
  }

  if (!property) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <p style={{ color: "#64748b" }}>Propriedade não encontrada.</p>
        <button
          onClick={() => navigate("/")}
          className="text-sm hover:underline"
          style={{ color: "#6c63ff" }}
        >
          Voltar
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Back + Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-sm mb-4 transition-colors hover:opacity-80"
          style={{ color: "#64748b" }}
        >
          <ArrowLeft size={16} />
          Voltar
        </button>

        <div className="flex items-start justify-between gap-4">
          <div>
            <h1
              className="text-xl font-bold leading-snug"
              style={{ color: "#e2e8f0" }}
            >
              {property.address || "Endereço não disponível"}
            </h1>
            <p className="text-sm mt-1" style={{ color: "#64748b" }}>
              {property.county && `${property.county}, `}
              {property.state}
              {property.source && (
                <span className="ml-2 opacity-60">· via {property.source}</span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <ScoreBadge score={property.score} size="lg" />
            <ClassificationBadge classification={property.classification ?? null} />
          </div>
        </div>
      </motion.div>

      {/* Action Buttons */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="flex flex-wrap gap-3"
      >
        <ActionButton
          href={buildGoogleMapsUrl(property.address ?? "")}
          icon={Map}
          label="Ver no Google Maps"
        />
        <ActionButton
          href={buildStreetViewUrl(property.lat, property.lng, property.address ?? "")}
          icon={Eye}
          label="Street View"
        />
        {property.listing_url && (
          <ActionButton
            href={property.listing_url}
            icon={ExternalLink}
            label={
              property.source === "cosl"
                ? "Ver no COSL"
                : property.source === "govease"
                ? "Ver no GovEase"
                : "Ver listagem original"
            }
            primary
          />
        )}
      </motion.div>

      {/* Main grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Dados básicos */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="rounded-xl p-5"
          style={{ backgroundColor: "#12121a", border: "1px solid #1e1e2e" }}
        >
          <h2 className="text-sm font-semibold mb-3" style={{ color: "#e2e8f0" }}>Dados Básicos</h2>
          {property.price != null && (
            <DataRow icon={DollarSign} label="Lance mínimo" value={formatCurrency(property.price)} />
          )}
          {property.acres != null && (
            <DataRow icon={Maximize2} label="Tamanho" value={formatAcres(property.acres)} />
          )}
          {property.price_per_acre != null && (
            <DataRow icon={DollarSign} label="Preço por acre" value={formatCurrency(property.price_per_acre)} />
          )}
          {property.discount_pct != null && (
            <DataRow
              icon={TrendingDown}
              label="Desconto vs. mercado"
              value={
                <span style={{ color: property.discount_pct >= 50 ? "#22c55e" : "#e2e8f0" }}>
                  {formatDiscount(property.discount_pct)}
                </span>
              }
            />
          )}
          {property.sale_date && (
            <DataRow
              icon={Calendar}
              label="Data do leilão"
              value={<span style={{ color: "#f59e0b" }}>{formatSaleDate(property.sale_date)}</span>}
            />
          )}
          {property.parcel_id && (
            <DataRow icon={MapPin} label="ID da parcela" value={<span className="font-mono text-xs">{property.parcel_id}</span>} />
          )}
          <DataRow icon={MapPin} label="Fonte" value={property.source.toUpperCase()} />
        </motion.div>

        {/* Mercado & Risco */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="rounded-xl p-5"
          style={{ backgroundColor: "#12121a", border: "1px solid #1e1e2e" }}
        >
          <h2 className="text-sm font-semibold mb-3" style={{ color: "#e2e8f0" }}>Mercado & Risco</h2>
          {property.fema_zone && (
            <DataRow
              icon={Shield}
              label="Zona FEMA"
              value={
                <span className="font-mono" style={{ color: property.fema_zone === "X" ? "#22c55e" : "#f59e0b" }}>
                  {property.fema_zone}
                </span>
              }
            />
          )}
          {property.population != null && (
            <DataRow
              icon={MapPin}
              label="Pop. do condado"
              value={property.population.toLocaleString("pt-BR")}
            />
          )}
          {property.median_hh_income != null && (
            <DataRow
              icon={TrendingDown}
              label="Renda mediana"
              value={new Intl.NumberFormat("pt-BR", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(property.median_hh_income)}
            />
          )}
          {property.lat != null && property.lng != null && (
            <DataRow
              icon={MapPin}
              label="Coordenadas"
              value={
                <span className="font-mono text-xs" style={{ color: "#64748b" }}>
                  {property.lat.toFixed(4)}, {property.lng.toFixed(4)}
                </span>
              }
            />
          )}
        </motion.div>
      </div>

      {/* Score Breakdown */}
      {property.score_breakdown && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.22 }}
          className="rounded-xl p-5"
          style={{ backgroundColor: "#12121a", border: "1px solid #1e1e2e" }}
        >
          <h2 className="text-sm font-semibold mb-4" style={{ color: "#e2e8f0" }}>Score Breakdown</h2>
          <div className="space-y-3">
            {[
              { label: "A — Desconto real", pts: property.score_breakdown.a_pts, max: 50, color: "#6c63ff" },
              { label: "B — Liquidez do mercado", pts: property.score_breakdown.b_pts, max: 35, color: "#22c55e" },
              { label: "C — Risco FEMA", pts: property.score_breakdown.c_pts, max: 15, color: "#f59e0b" },
            ].map(({ label, pts, max, color }) => (
              <div key={label}>
                <div className="flex justify-between text-xs mb-1" style={{ color: "#64748b" }}>
                  <span>{label}</span>
                  <span style={{ color: "#e2e8f0" }}>{pts} / {max}</span>
                </div>
                <div className="h-1.5 rounded-full" style={{ backgroundColor: "#1e1e2e" }}>
                  <div
                    className="h-1.5 rounded-full transition-all"
                    style={{ width: `${(pts / max) * 100}%`, backgroundColor: color }}
                  />
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* AI Analysis */}
      {property.ai_analysis && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.28 }}
          className="rounded-xl p-5 space-y-4"
          style={{ backgroundColor: "#12121a", border: "1px solid #1e1e2e" }}
        >
          <h2 className="text-sm font-semibold" style={{ color: "#64748b" }}>
            Análise Claude AI (opcional)
          </h2>
          <p className="text-sm leading-relaxed" style={{ color: "#64748b" }}>
            {property.ai_analysis.resumo}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: "#22c55e" }}>
                Pontos positivos
              </p>
              <ul className="space-y-1.5">
                {property.ai_analysis.pontos_positivos.map((p, i) => (
                  <li key={i} className="text-sm" style={{ color: "#64748b" }}>· {p}</li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: "#f59e0b" }}>
                Pontos de atenção
              </p>
              <ul className="space-y-1.5">
                {property.ai_analysis.pontos_atencao.map((p, i) => (
                  <li key={i} className="text-sm" style={{ color: "#64748b" }}>· {p}</li>
                ))}
              </ul>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}
