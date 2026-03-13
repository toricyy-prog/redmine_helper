import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import webhook
from app.routers import auth, api

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.issue_detection_mode == "polling":
        from app.services.poller import create_scheduler
        scheduler = create_scheduler()
        scheduler.start()
    yield


app = FastAPI(title="Redmine Helper", version="1.0.0", lifespan=lifespan)
app.include_router(webhook.router)
app.include_router(auth.router)
app.include_router(api.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


# Vue.js 정적 파일 서빙 (빌드된 파일이 있을 때만)
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{path:path}", include_in_schema=False)
    async def serve_spa(path: str = ""):
        """Vue.js SPA — 모든 경로에서 index.html 반환 (Vue Router가 처리)"""
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"error": "Frontend not built"}
