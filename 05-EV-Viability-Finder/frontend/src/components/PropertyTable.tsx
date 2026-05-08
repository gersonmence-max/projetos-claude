import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronUp, ChevronDown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import type { Property } from "../types";
import ScoreBadge from "./ScoreBadge";
import { formatCurrency, formatSaleDate } from "../lib/utils";

interface Props {
  data: Property[];
  isLoading: boolean;
}

const CLASSIFICATION_COLOR: Record<string, { bg: string; text: string }> = {
  FORTE:    { bg: "rgba(34,197,94,0.12)",   text: "#22c55e" },
  MODERADO: { bg: "rgba(251,191,36,0.12)",  text: "#f59e0b" },
  FRACO:    { bg: "rgba(100,116,139,0.12)", text: "#64748b" },
  EVITAR:   { bg: "rgba(239,68,68,0.12)",   text: "#ef4444" },
};

const columns: ColumnDef<Property>[] = [
  {
    accessorKey: "score",
    header: "Score",
    cell: ({ getValue }) => <ScoreBadge score={getValue() as number} size="sm" />,
    size: 80,
  },
  {
    accessorKey: "classification",
    header: "Classificação",
    size: 110,
    cell: ({ getValue }) => {
      const val = (getValue() as string | null) ?? "";
      const style = CLASSIFICATION_COLOR[val] ?? { bg: "transparent", text: "#64748b" };
      if (!val) return <span style={{ color: "#64748b" }}>—</span>;
      return (
        <span
          className="px-2 py-0.5 rounded text-xs font-semibold"
          style={{ backgroundColor: style.bg, color: style.text }}
        >
          {val}
        </span>
      );
    },
  },
  {
    accessorKey: "price",
    header: "Lance",
    size: 120,
    cell: ({ getValue }) => (
      <span style={{ color: "#e2e8f0" }}>{formatCurrency(getValue() as number)}</span>
    ),
  },
  {
    accessorKey: "price_per_acre",
    header: "$/Acre",
    size: 110,
    cell: ({ getValue }) => (
      <span style={{ color: "#64748b" }}>{formatCurrency(getValue() as number)}</span>
    ),
  },
  {
    accessorKey: "county",
    header: "Condado",
    size: 130,
    cell: ({ getValue }) => (
      <span style={{ color: "#e2e8f0" }}>{(getValue() as string) || "—"}</span>
    ),
  },
  {
    accessorKey: "population",
    header: "Pop.",
    size: 90,
    cell: ({ getValue }) => {
      const v = getValue() as number | undefined;
      return (
        <span style={{ color: "#64748b" }}>
          {v ? v.toLocaleString("pt-BR") : "—"}
        </span>
      );
    },
  },
  {
    accessorKey: "fema_zone",
    header: "FEMA",
    size: 70,
    cell: ({ getValue }) => {
      const zone = getValue() as string | null;
      return (
        <span
          className="text-xs font-mono font-semibold"
          style={{ color: zone === "X" ? "#22c55e" : zone ? "#f59e0b" : "#64748b" }}
        >
          {zone ?? "—"}
        </span>
      );
    },
  },
  {
    accessorKey: "sale_date",
    header: "Leilão",
    size: 110,
    cell: ({ getValue }) => (
      <span className="font-mono text-xs" style={{ color: "#64748b" }}>
        {formatSaleDate(getValue() as string | null)}
      </span>
    ),
  },
  {
    accessorKey: "state",
    header: "UF",
    size: 55,
    cell: ({ getValue }) => (
      <span
        className="font-mono text-xs px-1.5 py-0.5 rounded"
        style={{ backgroundColor: "rgba(108,99,255,0.1)", color: "#6c63ff" }}
      >
        {getValue() as string}
      </span>
    ),
  },
];

export default function PropertyTable({ data, isLoading }: Props) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: "score", desc: true },
  ]);
  const navigate = useNavigate();

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-3">
          <div
            className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin"
            style={{ borderColor: "#6c63ff", borderTopColor: "transparent" }}
          />
          <p className="text-sm" style={{ color: "#64748b" }}>
            Carregando terrenos...
          </p>
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="text-center">
          <p className="text-sm" style={{ color: "#64748b" }}>
            Nenhum terreno encontrado.
          </p>
          <p className="text-xs mt-1" style={{ color: "#64748b" }}>
            Rode o pipeline ou ajuste os filtros.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="overflow-x-auto rounded-xl"
      style={{ border: "1px solid #1e1e2e" }}
    >
      <table className="w-full text-sm">
        <thead>
          {table.getHeaderGroups().map((hg) => (
            <tr
              key={hg.id}
              style={{ borderBottom: "1px solid #1e1e2e", backgroundColor: "#12121a" }}
            >
              {hg.headers.map((header) => (
                <th
                  key={header.id}
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide whitespace-nowrap cursor-pointer select-none"
                  style={{ color: "#64748b", width: header.getSize() }}
                  onClick={header.column.getToggleSortingHandler()}
                >
                  <div className="flex items-center gap-1">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    {header.column.getIsSorted() === "asc" && <ChevronUp size={12} />}
                    {header.column.getIsSorted() === "desc" && <ChevronDown size={12} />}
                  </div>
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          <AnimatePresence>
            {table.getRowModel().rows.map((row, i) => (
              <motion.tr
                key={row.id}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.15, delay: i * 0.02 }}
                className="cursor-pointer"
                style={{ borderBottom: "1px solid rgba(30,30,46,0.5)" }}
                onClick={() => navigate(`/property/${row.original.id}`)}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.backgroundColor = "rgba(255,255,255,0.03)")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.backgroundColor = "transparent")
                }
              >
                {row.getVisibleCells().map((cell) => (
                  <td
                    key={cell.id}
                    className="px-4 py-3 whitespace-nowrap"
                    style={{ color: "#64748b" }}
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </motion.tr>
            ))}
          </AnimatePresence>
        </tbody>
      </table>
    </div>
  );
}
