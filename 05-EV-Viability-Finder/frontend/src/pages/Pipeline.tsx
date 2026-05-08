import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Play, Clock, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import type { PipelineRun } from "../types";
import { startPipeline, fetchPipelineHistory, openPipelineSSE } from "../api/pipeline";
import PipelineLog from "../components/PipelineLog";

function HistoryRow({ run }: { run: PipelineRun }) {
  const started = run.started_at ? new Date(run.started_at) : null;
  const finished = run.finished_at ? new Date(run.finished_at) : null;
  const duration =
    started && finished
      ? Math.round((finished.getTime() - started.getTime()) / 1000)
      : null;

  return (
    <div
      className="flex items-center gap-4 py-3"
      style={{ borderBottom: "1px solid rgba(30,30,46,0.5)" }}
    >
      <div className="flex-shrink-0">
        {run.status === "concluído" && (
          <CheckCircle2 size={16} style={{ color: "#22c55e" }} />
        )}
        {run.status === "erro" && (
          <XCircle size={16} style={{ color: "#ef4444" }} />
        )}
        {run.status === "rodando" && (
          <Loader2 size={16} className="animate-spin" style={{ color: "#6c63ff" }} />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3 text-sm">
          <span className="font-medium" style={{ color: "#e2e8f0" }}>
            {started?.toLocaleDateString("pt-BR")} às{" "}
            {started?.toLocaleTimeString("pt-BR", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
          {duration != null && (
            <span
              className="text-xs flex items-center gap-1"
              style={{ color: "#64748b" }}
            >
              <Clock size={11} />
              {duration}s
            </span>
          )}
        </div>
        <div
          className="flex items-center gap-4 mt-1 text-xs font-mono"
          style={{ color: "#64748b" }}
        >
          <span>{run.scraped} raspados</span>
          <span>{run.enriched} enriquecidos</span>
          <span>{run.filtered} filtrados</span>
          <span style={{ color: "#6c63ff" }}>{run.scored} pontuados</span>
        </div>
      </div>
    </div>
  );
}

export default function Pipeline() {
  const [isRunning, setIsRunning] = useState(false);
  const [currentRun, setCurrentRun] = useState<PipelineRun | null>(null);
  const [history, setHistory] = useState<PipelineRun[]>([]);

  const loadHistory = async () => {
    try {
      const data = await fetchPipelineHistory();
      setHistory(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleRun = async () => {
    if (isRunning) return;
    setIsRunning(true);

    try {
      const { run_id } = await startPipeline();

      setCurrentRun({
        id: run_id,
        status: "rodando",
        started_at: new Date().toISOString(),
        finished_at: null,
        scraped: 0,
        enriched: 0,
        filtered: 0,
        scored: 0,
        error_msg: null,
      });

      const cleanup = openPipelineSSE(
        run_id,
        (run) => setCurrentRun(run),
        () => {
          setIsRunning(false);
          loadHistory();
          cleanup();
        }
      );
    } catch (err) {
      console.error(err);
      setIsRunning(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold" style={{ color: "#e2e8f0" }}>
          Pipeline
        </h1>
        <p className="text-sm mt-1" style={{ color: "#64748b" }}>
          Dispara o scraping, enriquecimento, filtros e pontuação manualmente.
        </p>
      </motion.div>

      {/* Run Button */}
      <motion.div
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.1 }}
        className="rounded-xl p-6 flex flex-col items-center gap-4"
        style={{ backgroundColor: "#12121a", border: "1px solid #1e1e2e" }}
      >
        <button
          onClick={handleRun}
          disabled={isRunning}
          className="flex items-center gap-3 px-8 py-4 rounded-xl text-base font-semibold transition-all disabled:cursor-not-allowed"
          style={
            isRunning
              ? { backgroundColor: "rgba(108,99,255,0.2)", color: "#6c63ff" }
              : { backgroundColor: "#6c63ff", color: "#ffffff" }
          }
          onMouseEnter={(e) => {
            if (!isRunning)
              e.currentTarget.style.backgroundColor = "#5a52e0";
          }}
          onMouseLeave={(e) => {
            if (!isRunning)
              e.currentTarget.style.backgroundColor = "#6c63ff";
          }}
        >
          {isRunning ? (
            <>
              <Loader2 size={20} className="animate-spin" />
              Pipeline rodando...
            </>
          ) : (
            <>
              <Play size={20} />
              Rodar Pipeline
            </>
          )}
        </button>

        <p className="text-xs text-center max-w-sm" style={{ color: "#64748b" }}>
          O pipeline vai raspar listagens do Zillow em AL e AR, enriquecer com dados
          FEMA e Regrid, aplicar filtros e gerar scores automaticamente.
        </p>
      </motion.div>

      {/* Live Log */}
      {currentRun && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <PipelineLog run={currentRun} />
        </motion.div>
      )}

      {/* History */}
      {history.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="rounded-xl p-5"
          style={{ backgroundColor: "#12121a", border: "1px solid #1e1e2e" }}
        >
          <h3 className="text-sm font-semibold mb-4" style={{ color: "#e2e8f0" }}>
            Histórico de execuções
          </h3>
          {history.map((run) => (
            <HistoryRow key={run.id} run={run} />
          ))}
        </motion.div>
      )}
    </div>
  );
}
