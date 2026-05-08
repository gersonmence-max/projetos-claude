"""
app.py — Servidor Flask do ClipForge
Conecta o frontend (index.html) ao pipeline Python via WebSocket (SocketIO)

Instale as dependências antes de rodar:
    pip install -r requirements.txt

Para rodar:
    python app.py
    Acesse: http://localhost:5000
"""

import os
import json
import time
import threading
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request
from flask_socketio import SocketIO, emit
from pipeline import PipelineRunner

# ── App ───────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
CLIPS_DIR  = BASE_DIR / "clips"
CLIPS_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder=str(STATIC_DIR))
app.config["SECRET_KEY"] = "clipforge-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading", logger=False, engineio_logger=False, allowEIO3=True)

# ── Rotas HTML ────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)

# ── API REST ──────────────────────────────────────────────────────────────────
@app.route("/api/folders", methods=["GET"])
def get_folders():
    """Lista todas as pastas em ./clips/"""
    folders = []
    for p in sorted(CLIPS_DIR.iterdir()):
        if p.is_dir():
            clips = list(p.glob("*.mp4"))
            folders.append({
                "name":  p.name,
                "path":  str(p),
                "clips": len(clips),
            })
    return jsonify(folders)

@app.route("/api/folders", methods=["POST"])
def create_folder():
    """Cria uma nova pasta em ./clips/"""
    data = request.json
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Nome inválido"}), 400
    folder = CLIPS_DIR / name
    folder.mkdir(parents=True, exist_ok=True)
    return jsonify({"path": str(folder), "created": True})

@app.route("/api/folders/<name>", methods=["DELETE"])
def delete_folder(name):
    """Remove uma pasta e seus clips"""
    import shutil
    folder = CLIPS_DIR / name
    if not folder.exists():
        return jsonify({"error": "Pasta não encontrada"}), 404
    shutil.rmtree(folder)
    return jsonify({"deleted": True})

@app.route("/api/clips/<folder>", methods=["GET"])
def list_clips(folder):
    """Lista clips de uma pasta específica"""
    folder_path = CLIPS_DIR / folder
    if not folder_path.exists():
        return jsonify([])
    clips = []
    for mp4 in sorted(folder_path.rglob("*.mp4")):
        clips.append({
            "name":     mp4.name,
            "path":     str(mp4),
            "size_mb":  round(mp4.stat().st_size / (1024*1024), 1),
            "platform": mp4.stem.split("_")[-1] if "_" in mp4.stem else "local",
        })
    return jsonify(clips)

# ── WebSocket — pipeline em tempo real ───────────────────────────────────────
active_jobs = {}  # job_id → thread

@socketio.on("start_pipeline")
def handle_start(data):
    """
    Recebe do frontend:
    {
        url:        "https://youtube.com/...",
        folders:    ["pele", "marketing"],
        platforms:  ["yt", "tt"],
        sub_style:  "yellow",
        sub_font:   "Arial Black",
        sub_size:   52,
        n_clips:    8,
        min_score:  0.40,
        hw:         "cpu_fast"
    }
    """
    sid = request.sid

    def run():
        runner = PipelineRunner(
            sid        = sid,
            socketio   = socketio,
            clips_dir  = CLIPS_DIR,
            url        = data.get("url", ""),
            folders    = data.get("folders", []),
            platforms  = data.get("platforms", []),
            sub_style  = data.get("sub_style", "yellow"),
            sub_font   = data.get("sub_font", "Arial Black"),
            sub_size   = int(data.get("sub_size", 52)),
            n_clips    = int(data.get("n_clips", 8)),
            min_score  = float(data.get("min_score", 0.40)),
        )
        runner.run()

    t = threading.Thread(target=run, daemon=True)
    active_jobs[sid] = t
    t.start()

@socketio.on("cancel_pipeline")
def handle_cancel():
    sid = request.sid
    # Pipeline verifica flag de cancelamento internamente
    if sid in active_jobs:
        del active_jobs[sid]
    emit("pipeline_cancelled", {"msg": "Cancelado pelo usuário"})

@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    if sid in active_jobs:
        del active_jobs[sid]

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*50)
    print("  ClipForge — servidor iniciado")
    print("  Acesse: http://localhost:5000")
    print("="*50 + "\n")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
