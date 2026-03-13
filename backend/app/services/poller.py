import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.services.redmine_client import RedmineClient

logger = logging.getLogger(__name__)
_last_polled_at: datetime | None = None


async def poll_new_issues():
    """1분 이내 등록된 새 이슈 폴링"""
    global _last_polled_at
    client = RedmineClient()
    since = _last_polled_at or (datetime.utcnow() - timedelta(minutes=1))
    _last_polled_at = datetime.utcnow()
    logger.info(f"[폴링] {since.isoformat()} 이후 신규 이슈 확인 중...")
    # 실제 처리는 웹훅 핸들러와 동일한 process_webhook 호출 예정


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(poll_new_issues, "interval", minutes=1, id="issue_poller")
    return scheduler
