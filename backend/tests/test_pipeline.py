from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.analysis_pipeline import run_analysis


@pytest.mark.asyncio
async def test_pipeline_saves_to_db():
    """파이프라인 실행 시 analysis_history DB에 저장되는지 확인"""
    mock_issues = [{"id": 1, "subject": "유사 이슈", "description": "내용"}]
    mock_similar = [{"id": 1, "subject": "유사 이슈", "score": 0.8, "is_duplicate": False}]

    with patch("app.services.analysis_pipeline.RedmineClient") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.get_issues = AsyncMock(return_value=mock_issues)

        with patch("app.services.analysis_pipeline.SimilarityService") as MockSimilarity:
            mock_sim = MockSimilarity.return_value
            mock_sim.find_similar = MagicMock(return_value=mock_similar)

            mock_db = MagicMock()
            await run_analysis(
                issue_id=10,
                project_id=1,
                subject="로그인 오류",
                description="에러 발생",
                db=mock_db,
            )

            assert mock_db.add.called
            assert mock_db.commit.called
