from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


@pytest.mark.asyncio
async def test_pipeline_redmine_api_failure():
    """Redmine API 실패 시 status=failed, error_message에 에러 코드 기록"""
    with patch("app.services.analysis_pipeline.RedmineClient") as MockRC, \
         patch("app.services.analysis_pipeline.settings") as mock_settings:

        mock_settings.enable_auto_comment = False
        mock_rc = MockRC.return_value
        mock_rc.get_issues = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))

        mock_db = MagicMock()

        from app.services.analysis_pipeline import run_analysis
        await run_analysis(
            issue_id=1, project_id=1,
            subject="테스트", description="테스트",
            db=mock_db,
        )

        assert mock_db.add.called
        record = mock_db.add.call_args[0][0]
        assert record.status == "failed"
        assert "REDMINE_API_ERROR" in record.error_message


@pytest.mark.asyncio
async def test_pipeline_comment_write_failure_does_not_affect_db():
    """댓글 작성 실패해도 분석 결과는 DB에 저장됨"""
    mock_issues = [{"id": 1, "subject": "유사 이슈", "description": "내용"}]
    mock_similar = [{"id": 1, "subject": "유사 이슈", "score": 0.8, "is_duplicate": False}]

    with patch("app.services.analysis_pipeline.RedmineClient") as MockRC, \
         patch("app.services.analysis_pipeline.SimilarityService") as MockSim, \
         patch("app.services.analysis_pipeline.ClaudeClient") as MockClaude, \
         patch("app.services.analysis_pipeline.Classifier") as MockClassifier, \
         patch("app.services.analysis_pipeline.CommentWriter") as MockWriter, \
         patch("app.services.analysis_pipeline.settings") as mock_settings:

        mock_settings.enable_auto_comment = True
        mock_settings.redmine_url = "http://redmine.test"
        mock_settings.redmine_category_field_id = ""

        mock_rc = MockRC.return_value
        mock_rc.get_issues = AsyncMock(return_value=mock_issues)
        mock_rc.get_issue = AsyncMock(return_value={"journals": []})

        mock_sim = MockSim.return_value
        mock_sim.find_similar = MagicMock(return_value=mock_similar)

        mock_claude = MockClaude.return_value
        mock_claude.summarize = AsyncMock(return_value="AI 요약")

        mock_classifier = MockClassifier.return_value
        mock_classifier.classify = AsyncMock(return_value=None)

        mock_writer = MockWriter.return_value
        mock_writer.write_comment = AsyncMock(return_value=False)  # 댓글 작성 실패

        mock_db = MagicMock()

        from app.services.analysis_pipeline import run_analysis
        await run_analysis(
            issue_id=99, project_id=1,
            subject="테스트", description="테스트",
            db=mock_db,
        )

        # 댓글 실패해도 DB 저장은 성공
        assert mock_db.add.called
        assert mock_db.commit.called
        record = mock_db.add.call_args[0][0]
        assert record.status == "success"
        assert record.comment_written == 0
