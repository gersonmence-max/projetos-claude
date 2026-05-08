import { cn } from "../lib/utils";

interface Props {
  score: number | null | undefined;
  size?: "sm" | "md" | "lg";
}

function getColors(score: number | null | undefined) {
  if (score == null) return { color: "#64748b", bg: "transparent", border: "#1e1e2e" };
  if (score >= 70) return { color: "#22c55e", bg: "rgba(34,197,94,0.1)", border: "rgba(34,197,94,0.3)" };
  if (score >= 40) return { color: "#f59e0b", bg: "rgba(245,158,11,0.1)", border: "rgba(245,158,11,0.3)" };
  return { color: "#ef4444", bg: "rgba(239,68,68,0.1)", border: "rgba(239,68,68,0.3)" };
}

export default function ScoreBadge({ score, size = "md" }: Props) {
  if (score == null) return <span style={{ color: "#64748b", fontSize: "0.875rem" }}>—</span>;

  const { color, bg, border } = getColors(score);

  const sizeClass = {
    sm: "text-xs px-2 py-0.5 min-w-[3rem]",
    md: "text-sm px-2.5 py-1 min-w-[3.5rem]",
    lg: "text-2xl px-4 py-2 min-w-[5rem]",
  }[size];

  return (
    <span
      className={cn(
        "inline-flex items-center justify-center rounded-full border font-mono font-semibold",
        sizeClass
      )}
      style={{ color, backgroundColor: bg, borderColor: border }}
    >
      {score.toFixed(0)}
    </span>
  );
}
