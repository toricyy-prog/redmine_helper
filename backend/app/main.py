import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.routers import webhook

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


@app.get("/health")
async def health():
    return {"status": "ok"}
