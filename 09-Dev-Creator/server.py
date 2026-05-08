import sys
import queue
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="Dev Creator")

_jobs: dict[str, queue.Queue] = {}
_pipeline_lock = threading.Lock()
_is_running = False


class RunRequest(BaseModel):
    destination: str
    spec: str


class _QueueWriter:
    """Captures print() output from the pipeline thread into a queue."""
    def __init__(self, q: queue.Queue):
        self.q = q

    def write(self, text: str):
        if text and text.strip():
            self.q.put(text.rstrip())

    def flush(self):
        pass

    def isatty(self):
        return False


def _run_pipeline(job_id: str, destination: str, spec: str):
    global _is_running
    q = _jobs[job_id]
    old_stdout = sys.stdout
    sys.stdout = _QueueWriter(q)

    try:
        path = Path(destination.strip().strip('"').strip("'"))
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

        project_type = "greenfield" if not list(path.iterdir()) else "existing"

        from pipeline import run_pipeline
        run_pipeline(str(path), spec, project_type)
        q.put("__DONE__")

    except Exception as e:
        q.put(f"ERRO: {type(e).__name__}: {e}")
        q.put("__ERROR__")
    finally:
        sys.stdout = old_stdout
        _is_running = False
        _pipeline_lock.release()


@app.get("/", response_class=HTMLResponse)
def index():
    html = Path(__file__).parent / "templates" / "index.html"
    return HTMLResponse(html.read_text(encoding="utf-8"))


@app.post("/api/run")
def api_run(req: RunRequest):
    global _is_running

    if not req.destination.strip():
        raise HTTPException(status_code=400, detail="Pasta de destino vazia")
    if not req.spec.strip():
        raise HTTPException(status_code=400, detail="Especificacao vazia")

    if not _pipeline_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Ja existe uma execucao em andamento. Aguarde terminar.")

    _is_running = True
    job_id = str(uuid.uuid4())
    _jobs[job_id] = queue.Queue()

    threading.Thread(
        target=_run_pipeline,
        args=(job_id, req.destination, req.spec),
        daemon=True,
    ).start()

    return {"job_id": job_id}


@app.get("/api/stream/{job_id}")
def api_stream(job_id: str):
    def generate():
        q = _jobs.get(job_id)
        if not q:
            yield "data: Job nao encontrado\n\n"
            return
        try:
            while True:
                try:
                    msg = q.get(timeout=60)
                    if msg == "__DONE__":
                        yield "event: done\ndata: success\n\n"
                        break
                    elif msg == "__ERROR__":
                        yield "event: done\ndata: error\n\n"
                        break
                    else:
                        safe = msg.replace("\r", "").replace("\n", " ")
                        yield f"data: {safe}\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            _jobs.pop(job_id, None)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/status")
def api_status():
    return {"running": _is_running}
