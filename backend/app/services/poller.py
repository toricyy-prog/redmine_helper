import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.services.redmine_client import RedmineClient

logger = logging.getLogger(__name__)
_last_polled_at: datetime | None = None


async def poll_new_issues():
    """1분 이내 등록된 새 이슈 폴링 후 분석 파이프라인 실행"""
    global _last_polled_at
    from app.services.analysis_pipeline import run_analysis

    client = RedmineClient()
    since = _last_polled_at or (datetime.utcnow() - timedelta(minutes=1))
    _last_polled_at = datetime.utcnow()
    logger.info(f"[폴링] {since.isoformat()} 이후 신규 이슈 확인 중...")

    try:
        issues = await client.get_recent_issues(since)
    except Exception as e:
        logger.error(f"[폴링] Redmine API 조회 실패: {e}")
        return

    if not issues:
        logger.debug("[폴링] 신규 이슈 없음")
        return

    logger.info(f"[폴링] 신규 이슈 {len(issues)}건 발견, 분석 시작")
    for issue in issues:
        try:
            await run_analysis(
                issue_id=issue["id"],
                project_id=issue.get("project", {}).get("id", 0),
                subject=issue.get("subject", ""),
                description=issue.get("description", ""),
            )
        except Exception as e:
            logger.error(f"[폴링] 이슈 #{issue['id']} 분석 실패: {e}")


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(poll_new_issues, "interval", minutes=1, id="issue_poller")
    return scheduler
