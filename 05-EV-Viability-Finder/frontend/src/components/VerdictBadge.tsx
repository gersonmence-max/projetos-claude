type Verdict = "Oportunidade forte" | "Merece análise" | "Cautela" | null | undefined;

const STYLES: Record<string, { color: string; bg: string; border: string }> = {
  "Oportunidade forte": {
    color: "#22c55e",
    bg: "rgba(34,197,94,0.1)",
    border: "rgba(34,197,94,0.3)",
  },
  "Merece análise": {
    color: "#f59e0b",
    bg: "rgba(245,158,11,0.1)",
    border: "rgba(245,158,11,0.3)",
  },
  Cautela: {
    color: "#ef4444",
    bg: "rgba(239,68,68,0.1)",
    border: "rgba(239,68,68,0.3)",
  },
};

export default function VerdictBadge({ verdict }: { verdict: Verdict }) {
  if (!verdict) return <span style={{ color: "#64748b", fontSize: "0.75rem" }}>—</span>;

  const s = STYLES[verdict] ?? { color: "#64748b", bg: "#12121a", border: "#1e1e2e" };

  return (
    <span
      className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap"
      style={{ color: s.color, backgroundColor: s.bg, borderColor: s.border }}
    >
      {verdict}
    </span>
  );
}
