import { motion, AnimatePresence } from "framer-motion";
import type { PipelineRun } from "../types";

interface LogStep {
  label: string;
  value: number;
  total?: number;
  done: boolean;
  active: boolean;
}

function ProgressBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div
      className="h-1.5 rounded-full overflow-hidden"
      style={{ backgroundColor: "#1e1e2e" }}
    >
      <motion.div
        className="h-full rounded-full"
        style={{ backgroundColor: "#6c63ff" }}
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.5 }}
      />
    </div>
  );
}

export default function PipelineLog({ run }: { run: PipelineRun | null }) {
  if (!run) return null;

  const steps: LogStep[] = [
    {
      label: "Raspando listagens (Zillow + GIS)",
      value: run.scraped,
      done: run.enriched > 0,
      active: run.scraped === 0 && run.status === "rodando",
    },
    {
      label: "Enriquecendo dados (FEMA + Regrid)",
      value: run.enriched,
      total: run.scraped,
      done: run.filtered > 0,
      active: run.enriched > 0 && run.filtered === 0,
    },
    {
      label: "Aplicando filtros",
      value: run.filtered,
      total: run.enriched,
      done: run.scored > 0,
      active: run.filtered > 0 && run.scored === 0,
    },
    {
      label: "Pontuando e analisando com IA",
      value: run.scored,
      total: run.filtered,
      done: run.status === "concluído",
      active: run.scored > 0 && run.status === "rodando",
    },
  ];

  const statusColor =
    run.status === "concluído"
      ? "#22c55e"
      : run.status === "erro"
      ? "#ef4444"
      : "#6c63ff";

  return (
    <div
      className="rounded-xl p-5 space-y-4"
      style={{ backgroundColor: "#12121a", border: "1px solid #1e1e2e" }}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold" style={{ color: "#e2e8f0" }}>
          Progresso
        </h3>
        <span
          className="text-xs font-medium px-2.5 py-1 rounded-full border"
          style={{
            color: statusColor,
            backgroundColor: `${statusColor}1a`,
            borderColor: `${statusColor}4d`,
          }}
        >
          {run.status}
        </span>
      </div>

      <div className="space-y-4">
        <AnimatePresence>
          {steps.map((step, i) => (
            <motion.div
              key={step.label}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="space-y-1.5"
            >
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2" style={{ color: "#64748b" }}>
                  <div
                    className="w-1.5 h-1.5 rounded-full"
                    style={{
                      backgroundColor: step.done
                        ? "#22c55e"
                        : step.active
                        ? "#6c63ff"
                        : "#1e1e2e",
                    }}
                  />
                  {step.label}
                </div>
                <span className="font-mono" style={{ color: "#64748b" }}>
                  {step.value}
                  {step.total ? `/${step.total}` : ""}
                </span>
              </div>
              {step.total != null && step.total > 0 && (
                <ProgressBar value={step.value} max={step.total} />
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {run.error_msg && (
        <div
          className="mt-3 p-3 rounded-lg"
          style={{
            backgroundColor: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
          }}
        >
          <p className="text-xs font-mono" style={{ color: "#ef4444" }}>
            {run.error_msg}
          </p>
        </div>
      )}
    </div>
  );
}
