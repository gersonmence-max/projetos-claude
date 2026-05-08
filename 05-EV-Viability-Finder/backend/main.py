# backend/main.py
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from database import Base, engine
from routes.pipeline import router as pipeline_router
from routes.properties import router as properties_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Buscador de Terrenos", version="1.0.0")

# ── Rotas da API (prefixo /api) ────────────────────────────────────────────────
app.include_router(properties_router, prefix="/api")
app.include_router(pipeline_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


# ── Servir o frontend compilado ────────────────────────────────────────────────
DIST = Path(__file__).parent.parent / "frontend" / "dist"

if DIST.exists():
    # Arquivos com hash (JS, CSS) ficam em dist/assets/
    assets_dir = DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """
        Serve arquivos estáticos da raiz do dist (favicon, icons…)
        ou retorna index.html para qualquer rota do SPA.
        """
        # Tenta servir o arquivo exato primeiro (ex: /favicon.svg)
        candidate = DIST / full_path
        if candidate.is_file():
            return FileResponse(str(candidate))

        # Fallback: retorna index.html para rotas do React (SPA)
        index = DIST / "index.html"
        if index.exists():
            return FileResponse(str(index))

        return JSONResponse(
            {"erro": "Frontend não compilado. Execute: cd frontend && npm run build"},
            status_code=503,
        )
else:
    @app.get("/{full_path:path}", include_in_schema=False)
    async def frontend_not_built(full_path: str):
        return JSONResponse(
            {"erro": "Frontend não compilado. Execute: cd frontend && npm run build"},
            status_code=503,
        )
