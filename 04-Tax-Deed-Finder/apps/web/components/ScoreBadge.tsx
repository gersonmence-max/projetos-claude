export default function ScoreBadge({ score }: { score: number | null | undefined }) {
  if (score == null) return <span className="text-parchment-dim text-sm font-mono">—</span>;

  let cls = "";
  if (score >= 90)      cls = "bg-gold-light text-bg-primary ring-1 ring-gold-light/50";
  else if (score >= 75) cls = "bg-gold-bright text-bg-primary ring-1 ring-gold-bright/40";
  else if (score >= 60) cls = "bg-gold-muted text-parchment ring-1 ring-gold-muted/40";
  else                  cls = "bg-gold-dim text-parchment-muted ring-1 ring-gold-dim/30";

  return (
    <span className={`inline-flex items-center justify-center w-10 h-10 rounded-full font-mono font-medium text-sm ${cls}`}>
      {score}
    </span>
  );
}
