from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.claude_client import ClaudeClient


@pytest.mark.asyncio
async def test_summarize_similar_issues_success():
    """유사 이슈 목록으로 AI 요약 생성 성공"""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="## 해결 방법 요약\n유사한 로그인 오류는 세션 만료가 원인이었습니다.")]

    with patch("app.services.claude_client.anthropic.AsyncAnthropic") as MockAnthropic:
        mock_client = MockAnthropic.return_value
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        client = ClaudeClient(api_key="test_key")
        similar_issues = [
            {"id": 1, "subject": "로그인 오류", "score": 0.85, "comments": ["세션 만료로 해결"]},
        ]
        result = await client.summarize(
            new_issue_subject="로그인 페이지 500 오류",
            new_issue_description="로그인 시 500 에러 발생",
            similar_issues=similar_issues,
        )
        assert result is not None
        assert len(result) > 0


@pytest.mark.asyncio
async def test_summarize_api_failure_with_retry():
    """API 실패 시 1회 재시도 후 None 반환"""
    with patch("app.services.claude_client.anthropic.AsyncAnthropic") as MockAnthropic:
        mock_client = MockAnthropic.return_value
        mock_client.messages.create = AsyncMock(side_effect=Exception("API Error"))

        client = ClaudeClient(api_key="test_key")
        result = await client.summarize(
            new_issue_subject="테스트",
            new_issue_description="테스트 설명",
            similar_issues=[{"id": 1, "subject": "유사", "score": 0.5, "comments": []}],
        )
        assert result is None
        # 2회 호출 확인 (최초 1회 + 재시도 1회)
        assert mock_client.messages.create.call_count == 2


@pytest.mark.asyncio
async def test_summarize_empty_similar_issues():
    """유사 이슈 없으면 Claude API 호출 없이 None 반환"""
    with patch("app.services.claude_client.anthropic.AsyncAnthropic") as MockAnthropic:
        mock_client = MockAnthropic.return_value
        mock_client.messages.create = AsyncMock()

        client = ClaudeClient(api_key="test_key")
        result = await client.summarize(
            new_issue_subject="테스트",
            new_issue_description="테스트 설명",
            similar_issues=[],
        )
        assert result is None
        mock_client.messages.create.assert_not_called()


def test_prompt_truncates_to_2000_chars():
    """프롬프트 내용이 2000자 이내로 구성되는지 확인"""
    client = ClaudeClient(api_key="test_key")
    long_description = "a" * 3000
    similar_issues = [
        {"id": i, "subject": f"이슈 {i}", "score": 0.5, "comments": ["b" * 500]}
        for i in range(5)
    ]
    prompt = client._build_prompt(
        new_issue_subject="테스트",
        new_issue_description=long_description,
        similar_issues=similar_issues,
    )
    assert len(prompt) <= 2500
