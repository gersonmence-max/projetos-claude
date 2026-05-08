import type { PropertyFilters } from "../types";

interface Props {
  filters: PropertyFilters;
  onChange: (filters: PropertyFilters) => void;
}

function FilterInput({
  label,
  value,
  onChange,
  placeholder,
  prefix,
  suffix,
}: {
  label: string;
  value: number | undefined;
  onChange: (v: number | undefined) => void;
  placeholder: string;
  prefix?: string;
  suffix?: string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium uppercase tracking-wide" style={{ color: "#64748b" }}>
        {label}
      </label>
      <div
        className="flex items-center gap-1 rounded-lg px-3 py-2"
        style={{ backgroundColor: "#12121a", border: "1px solid #1e1e2e" }}
      >
        {prefix && <span className="text-sm" style={{ color: "#64748b" }}>{prefix}</span>}
        <input
          type="number"
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value ? Number(e.target.value) : undefined)}
          placeholder={placeholder}
          className="flex-1 bg-transparent text-sm outline-none min-w-0"
          style={{ color: "#e2e8f0" }}
        />
        {suffix && <span className="text-sm" style={{ color: "#64748b" }}>{suffix}</span>}
      </div>
    </div>
  );
}

function SelectFilter({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string | undefined;
  onChange: (v: string | undefined) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium uppercase tracking-wide" style={{ color: "#64748b" }}>
        {label}
      </label>
      <select
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value || undefined)}
        className="rounded-lg px-3 py-2 text-sm outline-none"
        style={{ backgroundColor: "#0a0a0f", border: "1px solid #1e1e2e", color: "#e2e8f0" }}
      >
        <option value="">Todos</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

export default function FilterPanel({ filters, onChange }: Props) {
  return (
    <div
      className="rounded-xl p-4 space-y-4"
      style={{ backgroundColor: "#12121a", border: "1px solid #1e1e2e" }}
    >
      <h3 className="text-sm font-semibold" style={{ color: "#e2e8f0" }}>Filtros</h3>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <SelectFilter
          label="Estado"
          value={filters.state}
          onChange={(v) => onChange({ ...filters, state: v })}
          options={[{ value: "AL", label: "Alabama" }, { value: "AR", label: "Arkansas" }]}
        />

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium uppercase tracking-wide" style={{ color: "#64748b" }}>
            Condado
          </label>
          <div
            className="flex items-center gap-1 rounded-lg px-3 py-2"
            style={{ backgroundColor: "#12121a", border: "1px solid #1e1e2e" }}
          >
            <input
              type="text"
              value={filters.county ?? ""}
              onChange={(e) => onChange({ ...filters, county: e.target.value || undefined })}
              placeholder="Jefferson..."
              className="flex-1 bg-transparent text-sm outline-none min-w-0"
              style={{ color: "#e2e8f0" }}
            />
          </div>
        </div>

        <SelectFilter
          label="Classificação"
          value={filters.classification}
          onChange={(v) => onChange({ ...filters, classification: v })}
          options={[
            { value: "FORTE", label: "FORTE" },
            { value: "MODERADO", label: "MODERADO" },
            { value: "FRACO", label: "FRACO" },
            { value: "EVITAR", label: "EVITAR" },
          ]}
        />

        <FilterInput
          label="Score mín."
          value={filters.min_score}
          onChange={(v) => onChange({ ...filters, min_score: v })}
          placeholder="0"
        />
        <FilterInput
          label="Preço máximo"
          value={filters.max_price}
          onChange={(v) => onChange({ ...filters, max_price: v })}
          placeholder="500000"
          prefix="$"
        />
        <FilterInput
          label="Tamanho mín."
          value={filters.min_acres}
          onChange={(v) => onChange({ ...filters, min_acres: v })}
          placeholder="1"
          suffix="ac"
        />
        <FilterInput
          label="Desconto mín."
          value={filters.min_discount_pct}
          onChange={(v) => onChange({ ...filters, min_discount_pct: v })}
          placeholder="50"
          suffix="%"
        />
      </div>

      <div className="flex items-center justify-end pt-1">
        <button
          onClick={() => onChange({})}
          className="text-xs transition-colors hover:opacity-80"
          style={{ color: "#64748b" }}
        >
          Limpar filtros
        </button>
      </div>
    </div>
  );
}
