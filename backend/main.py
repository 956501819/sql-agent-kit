import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.routers import query, analysis, history, config, fewshot, tables, annotations, params, suggestions, run_sql

app = FastAPI(title="sql-agent-kit API", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes — must be registered before the catch-all SPA route
app.include_router(query.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(fewshot.router, prefix="/api")
app.include_router(tables.router, prefix="/api")
app.include_router(annotations.router, prefix="/api")
app.include_router(params.router, prefix="/api")
app.include_router(suggestions.router, prefix="/api")
app.include_router(run_sql.router, prefix="/api")

# Serve Vue SPA static assets
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

if os.path.exists(STATIC_DIR):
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Catch-all: serve index.html for Vue Router history mode."""
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
