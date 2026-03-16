"""Sprint 4 — 안정성 & 에러 처리 강화 테스트"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_concurrent_same_issue_uses_lock():
    """동일 이슈 동시 분석 시 이슈 레벨 락으로 순차 처리"""
    call_order = []

    async def fake_run(issue_id, project_id, subject, description, db=None, force_comment=False):
        call_order.append(f"start-{issue_id}")
        await asyncio.sleep(0)
        call_order.append(f"end-{issue_id}")

    # _issue_locks 초기화
    from app.services import analysis_pipeline
    analysis_pipeline._issue_locks.clear()

    with patch("app.services.analysis_pipeline.RedmineClient"), \
         patch("app.services.analysis_pipeline.SimilarityService"), \
         patch("app.services.analysis_pipeline.ClaudeClient"), \
         patch("app.services.analysis_pipeline.Classifier"), \
         patch("app.services.analysis_pipeline.CommentWriter"), \
         patch("app.services.analysis_pipeline.SessionLocal"), \
         patch("app.services.analysis_pipeline.settings"):

        # run_analysis 내부를 fake로 대체하지 않고 락 동작만 확인
        # 같은 issue_id에 대해 락이 공유되는지 확인
        lock1 = await analysis_pipeline._get_issue_lock(42)
        lock2 = await analysis_pipeline._get_issue_lock(42)
        lock3 = await analysis_pipeline._get_issue_lock(99)

        assert lock1 is lock2  # 같은 이슈 → 같은 락 객체
        assert lock1 is not lock3  # 다른 이슈 → 다른 락 객체


@pytest.mark.asyncio
async def test_post_comment_retries_on_failure():
    """post_comment 실패 시 3회까지 재시도"""
    import httpx
    from app.services.redmine_client import RedmineClient

    client = RedmineClient(base_url="http://test.example", api_key="key")
    attempt_count = 0

    async def mock_put(*args, **kwargs):
        nonlocal attempt_count
        attempt_count += 1
        raise httpx.ConnectError("connection refused")

    with patch("httpx.AsyncClient") as MockClient:
        mock_http = MagicMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.put = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
        MockClient.return_value = mock_http

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(httpx.ConnectError):
                await client.post_comment(issue_id=1, comment="test")

        # 3회 시도 확인
        assert mock_http.put.call_count == 3


@pytest.mark.asyncio
async def test_pipeline_redmine_error_saved_to_db():
    """Redmine API 오류 시 DB에 failed 상태 저장"""
    import httpx
    from unittest.mock import MagicMock, AsyncMock, patch

    mock_db = MagicMock()

    with patch("app.services.analysis_pipeline.RedmineClient") as MockRC, \
         patch("app.services.analysis_pipeline.settings") as mock_settings:

        mock_settings.enable_auto_comment = False
        mock_settings.redmine_url = "http://redmine.test"
        mock_settings.redmine_category_field_id = ""
        mock_settings.issue_search_days = 365

        mock_rc = MockRC.return_value
        mock_rc.get_issues = AsyncMock(side_effect=httpx.ConnectError("fail"))

        from app.services.analysis_pipeline import run_analysis
        await run_analysis(
            issue_id=55, project_id=1,
            subject="테스트", description="내용",
            db=mock_db,
        )

    # DB에 failed 기록 저장 확인
    assert mock_db.add.called
    saved_record = mock_db.add.call_args[0][0]
    assert saved_record.status == "failed"
    assert "REDMINE_API_ERROR" in saved_record.error_message
