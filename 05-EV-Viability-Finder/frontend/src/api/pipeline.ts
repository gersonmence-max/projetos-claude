import type { PipelineRun } from "../types";
import client from "./client";

export async function startPipeline(): Promise<{ run_id: number; status: string }> {
  const { data } = await client.post("/pipeline/run");
  return data;
}

export async function fetchPipelineHistory(): Promise<PipelineRun[]> {
  const { data } = await client.get<PipelineRun[]>("/pipeline/history");
  return data;
}

export function openPipelineSSE(
  runId: number,
  onMessage: (run: PipelineRun) => void,
  onDone: () => void
): () => void {
  const es = new EventSource(`/api/pipeline/status/${runId}`);

  es.onmessage = (event) => {
    const payload = JSON.parse(event.data) as PipelineRun;
    onMessage(payload);
    if (payload.status === "concluído" || payload.status === "erro") {
      es.close();
      onDone();
    }
  };

  es.onerror = () => {
    es.close();
    onDone();
  };

  return () => es.close();
}
