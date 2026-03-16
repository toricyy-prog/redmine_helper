from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_classify_issue_success():
    """이슈 카테고리 분류 성공 — 신뢰도 임계값 이상"""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"category": "버그", "confidence": 0.92}')]

    with patch("app.services.classifier.anthropic.AsyncAnthropic") as MockAnthropic:
        mock_client = MockAnthropic.return_value
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        from app.services.classifier import Classifier

        classifier = Classifier(
            api_key="test_key",
            categories=["버그", "기능요청", "문의"],
            threshold=0.7,
        )
        result = await classifier.classify(subject="로그인 500 에러", description="로그인 시 서버 오류")
        assert result is not None
        assert result["category"] == "버그"
        assert result["confidence"] >= 0.7


@pytest.mark.asyncio
async def test_classify_below_threshold_returns_none():
    """신뢰도 임계값 미만 시 None 반환 (분류 보류)"""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"category": "문의", "confidence": 0.45}')]

    with patch("app.services.classifier.anthropic.AsyncAnthropic") as MockAnthropic:
        mock_client = MockAnthropic.return_value
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        from app.services.classifier import Classifier

        classifier = Classifier(
            api_key="test_key",
            categories=["버그", "기능요청", "문의"],
            threshold=0.7,
        )
        result = await classifier.classify(subject="이게 뭔가요", description="잘 모르겠어요")
        assert result is None


@pytest.mark.asyncio
async def test_classify_api_failure_returns_none():
    """Claude API 실패 시 None 반환"""
    with patch("app.services.classifier.anthropic.AsyncAnthropic") as MockAnthropic:
        mock_client = MockAnthropic.return_value
        mock_client.messages.create = AsyncMock(side_effect=Exception("API Error"))

        from app.services.classifier import Classifier

        classifier = Classifier(api_key="test_key", categories=["버그"], threshold=0.7)
        result = await classifier.classify(subject="테스트", description="테스트")
        assert result is None


@pytest.mark.asyncio
async def test_classify_invalid_json_returns_none():
    """Claude API가 유효하지 않은 JSON 반환 시 None 반환"""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="분류할 수 없습니다.")]

    with patch("app.services.classifier.anthropic.AsyncAnthropic") as MockAnthropic:
        mock_client = MockAnthropic.return_value
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        from app.services.classifier import Classifier

        classifier = Classifier(api_key="test_key", categories=["버그"], threshold=0.7)
        result = await classifier.classify(subject="테스트", description="테스트")
        assert result is None
