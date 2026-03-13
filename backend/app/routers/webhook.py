import hashlib
import hmac
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.config import settings
from app.schemas.webhook import RedmineWebhookPayload

router = APIRouter(prefix="/webhook", tags=["webhook"])
logger = logging.getLogger(__name__)


def verify_signature(body: bytes, token: str) -> bool:
    expected = hmac.new(settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, token)


async def process_webhook(issue_id: int, project_id: int, subject: str, description: str):
    from app.services.analysis_pipeline import run_analysis
    await run_analysis(issue_id=issue_id, project_id=project_id, subject=subject, description=description)


@router.post("/redmine")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    token = request.headers.get("X-Redmine-Token", "")
    if not verify_signature(body, token):
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    try:
        payload = RedmineWebhookPayload.model_validate_json(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")

    # issue_created 이벤트만 처리
    if payload.action not in ("opened", "created"):
        return {"status": "ignored"}

    background_tasks.add_task(
        process_webhook,
        payload.issue.id,
        payload.issue.project["id"],
        payload.issue.subject,
        payload.issue.description or ""
    )
    from fastapi.responses import JSONResponse
    return JSONResponse(content={"status": "accepted"}, status_code=202)
