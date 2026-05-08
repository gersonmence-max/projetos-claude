#!/usr/bin/env python3
# ============================================================
#  run.py — Inicia a API
#  Desenvolvimento: python run.py
#  Producao:        uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
# ============================================================

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

import uvicorn

if __name__ == "__main__":
    env = os.environ.get("ENVIRONMENT", "development")
    is_dev = env == "development"

    uvicorn.run(
        "api.main:app",
        host    = "0.0.0.0",
        port    = int(os.environ.get("PORT", 8000)),
        reload  = is_dev,
        workers = 1 if is_dev else 4,
        log_level = "info",
    )
