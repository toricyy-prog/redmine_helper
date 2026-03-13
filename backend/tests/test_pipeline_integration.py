from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_full_pipeline_with_auto_comment_disabled():
    """ENABLE_AUTO_COMMENT=false 시 전체 파이프라인 — 댓글 미작성"""
    mock_issues = [{"id": 1, "subject": "로그인 오류", "description": "에러"}]
    mock_similar = [{"id": 1, "subject": "로그인 오류", "score": 0.8, "is_duplicate": False}]

    with patch("app.services.analysis_pipeline.RedmineClient") as MockRC, \
         patch("app.services.analysis_pipeline.SimilarityService") as MockSim, \
         patch("app.services.analysis_pipeline.ClaudeClient") as MockClaude, \
         patch("app.services.analysis_pipeline.Classifier") as MockClassifier, \
         patch("app.services.analysis_pipeline.CommentWriter") as MockWriter, \
         patch("app.services.analysis_pipeline.settings") as mock_settings:

        mock_settings.enable_auto_comment = False
        mock_settings.redmine_url = "http://redmine.test"
        mock_settings.redmine_category_field_id = ""

        mock_rc = MockRC.return_value
        mock_rc.get_issues = AsyncMock(return_value=mock_issues)
        mock_rc.get_issue = AsyncMock(return_value={"journals": []})

        mock_sim = MockSim.return_value
        mock_sim.find_similar = MagicMock(return_value=mock_similar)

        mock_claude = MockClaude.return_value
        mock_claude.summarize = AsyncMock(return_value="AI 요약 내용")

        mock_classifier = MockClassifier.return_value
        mock_classifier.classify = AsyncMock(return_value={"category": "버그", "confidence": 0.9})

        mock_writer = MockWriter.return_value
        mock_writer.write_comment = AsyncMock(return_value=False)

        mock_db = MagicMock()

        from app.services.analysis_pipeline import run_analysis
        await run_analysis(
            issue_id=99, project_id=1,
            subject="로그인 페이지 오류", description="에러 발생",
            db=mock_db,
        )

        assert mock_db.add.called
        assert mock_db.commit.called


@pytest.mark.asyncio
async def test_full_pipeline_claude_failure_fallback():
    """Claude API 실패 시 유사 이슈 목록만으로 댓글 작성 (ENABLE_AUTO_COMMENT=true)"""
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
        mock_claude.summarize = AsyncMock(return_value=None)  # Claude 실패

        mock_classifier = MockClassifier.return_value
        mock_classifier.classify = AsyncMock(return_value=None)

        mock_writer = MockWriter.return_value
        mock_writer.write_comment = AsyncMock(return_value=True)

        mock_db = MagicMock()

        from app.services.analysis_pipeline import run_analysis
        await run_analysis(
            issue_id=99, project_id=1,
            subject="테스트 이슈", description="에러 발생",
            db=mock_db,
        )

        # 요약 없이도 댓글 작성 시도 확인
        mock_writer.write_comment.assert_called_once()
        call_kwargs = mock_writer.write_comment.call_args.kwargs
        assert call_kwargs.get("ai_summary") is None
        assert call_kwargs.get("similar_issues") == mock_similar


@pytest.mark.asyncio
async def test_full_pipeline_no_similar_issues():
    """유사 이슈 없을 때 status=no_similar, Claude API 미호출"""
    with patch("app.services.analysis_pipeline.RedmineClient") as MockRC, \
         patch("app.services.analysis_pipeline.SimilarityService") as MockSim, \
         patch("app.services.analysis_pipeline.ClaudeClient") as MockClaude, \
         patch("app.services.analysis_pipeline.Classifier") as MockClassifier, \
         patch("app.services.analysis_pipeline.CommentWriter"), \
         patch("app.services.analysis_pipeline.settings") as mock_settings:

        mock_settings.enable_auto_comment = True
        mock_settings.redmine_url = "http://redmine.test"
        mock_settings.redmine_category_field_id = ""

        mock_rc = MockRC.return_value
        mock_rc.get_issues = AsyncMock(return_value=[])

        mock_sim = MockSim.return_value
        mock_sim.find_similar = MagicMock(return_value=[])

        mock_claude = MockClaude.return_value
        mock_claude.summarize = AsyncMock()

        mock_classifier = MockClassifier.return_value
        mock_classifier.classify = AsyncMock(return_value=None)

        mock_db = MagicMock()

        from app.services.analysis_pipeline import run_analysis
        await run_analysis(
            issue_id=99, project_id=1,
            subject="완전히 새로운 이슈", description="새 내용",
            db=mock_db,
        )

        # 유사 이슈 없으므로 Claude API 호출 없음
        mock_claude.summarize.assert_not_called()
        assert mock_db.add.called
