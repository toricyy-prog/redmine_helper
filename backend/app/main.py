import json
import logging
import logging.config
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import webhook
from app.routers import auth, api


# ── JSON 구조화 로그 설정 ───────────────────────────────────────────────────

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "time": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)


def _setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]


_setup_logging()
logger = logging.getLogger(__name__)


# ── 분석 이력 90일 자동 정리 ────────────────────────────────────────────────

async def cleanup_old_analysis():
    """90일 이상 된 분석 이력 삭제"""
    from app.db.session import SessionLocal
    from app.models.analysis import AnalysisHistory

    cutoff = datetime.utcnow() - timedelta(days=90)
    db = SessionLocal()
    try:
        deleted = (
            db.query(AnalysisHistory)
            .filter(AnalysisHistory.created_at < cutoff)
            .delete(synchronize_session=False)
        )
        db.commit()
        if deleted:
            logger.info(f"[정리] 90일 이상 분석 이력 {deleted}건 삭제 완료")
    except Exception as e:
        logger.error(f"[정리] 이력 삭제 실패: {e}")
    finally:
        db.close()


# ── 앱 생명주기 ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()

    if settings.issue_detection_mode == "polling":
        from app.services.poller import poll_new_issues
        scheduler.add_job(poll_new_issues, "interval", minutes=1, id="issue_poller")
        logger.info("[Startup] 폴링 모드 활성화 (1분 주기)")

    # 매일 자정 90일 이상 이력 정리
    scheduler.add_job(cleanup_old_analysis, "cron", hour=0, minute=0, id="history_cleanup")
    scheduler.start()

    yield

    scheduler.shutdown(wait=False)


app = FastAPI(title="Redmine Helper", version="1.0.0", lifespan=lifespan)
app.include_router(webhook.router)
app.include_router(auth.router)
app.include_router(api.router)


# ── 헬스체크 ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    checks: dict = {}

    # DB 연결 확인
    try:
        from app.db.session import SessionLocal
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {e}"

    # Redmine 설정 확인
    if settings.redmine_url and settings.redmine_api_key:
        checks["redmine"] = "configured"
    else:
        checks["redmine"] = "not_configured"

    # Claude API 설정 확인
    if settings.claude_api_key:
        checks["claude"] = "configured"
    else:
        checks["claude"] = "not_configured"

    overall = "ok" if checks["db"] == "ok" else "degraded"
    return {"status": overall, "checks": checks}


# ── Vue.js 정적 파일 서빙 ────────────────────────────────────────────────────

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
