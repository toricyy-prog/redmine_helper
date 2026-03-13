from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.comment_writer import CommentWriter, build_comment_body


def test_build_comment_body_with_summary():
    """AI 요약이 있을 때 댓글 형식 검증"""
    similar_issues = [
        {"id": 1, "subject": "로그인 오류", "score": 0.85, "is_duplicate": False},
        {"id": 2, "subject": "세션 만료", "score": 0.72, "is_duplicate": False},
    ]
    body = build_comment_body(
        similar_issues=similar_issues,
        ai_summary="세션 만료 시 쿠키 초기화로 해결한 사례가 있습니다.",
        redmine_url="http://redmine.example.com",
        is_duplicate=False,
    )
    assert "[Redmine Helper 자동 분석]" in body
    assert "세션 만료 시 쿠키 초기화" in body
    assert "#1" in body
    assert "85%" in body
    assert "#2" in body
    assert "72%" in body


def test_build_comment_body_without_summary():
    """AI 요약 없을 때 이슈 목록만 포함"""
    similar_issues = [{"id": 1, "subject": "유사 이슈", "score": 0.6, "is_duplicate": False}]
    body = build_comment_body(
        similar_issues=similar_issues,
        ai_summary=None,
        redmine_url="http://redmine.example.com",
        is_duplicate=False,
    )
    assert "[Redmine Helper 자동 분석]" in body
    assert "#1" in body
    assert "AI 요약을 생성할 수 없" in body


def test_build_comment_body_duplicate_warning():
    """중복 감지 시 경고 댓글 형식"""
    similar_issues = [{"id": 1, "subject": "동일 이슈", "score": 0.95, "is_duplicate": True}]
    body = build_comment_body(
        similar_issues=similar_issues,
        ai_summary=None,
        redmine_url="http://redmine.example.com",
        is_duplicate=True,
    )
    assert "중복 의심" in body
    assert "95%" in body


@pytest.mark.asyncio
async def test_write_comment_disabled_by_flag():
    """ENABLE_AUTO_COMMENT=false 시 Redmine API 호출 없음"""
    with patch("app.services.comment_writer.settings") as mock_settings:
        mock_settings.enable_auto_comment = False
        mock_redmine = MagicMock()
        mock_redmine.post_comment = AsyncMock()

        writer = CommentWriter(redmine_client=mock_redmine)
        result = await writer.write_comment(
            issue_id=1,
            similar_issues=[],
            ai_summary=None,
            redmine_url="http://redmine.example.com",
            is_duplicate=False,
        )
        assert result is False
        mock_redmine.post_comment.assert_not_called()


@pytest.mark.asyncio
async def test_write_comment_enabled_by_flag():
    """ENABLE_AUTO_COMMENT=true 시 Redmine에 댓글 작성"""
    with patch("app.services.comment_writer.settings") as mock_settings:
        mock_settings.enable_auto_comment = True
        mock_redmine = MagicMock()
        mock_redmine.post_comment = AsyncMock()
        mock_redmine.get_issue = AsyncMock(return_value={"journals": []})

        writer = CommentWriter(redmine_client=mock_redmine)
        result = await writer.write_comment(
            issue_id=1,
            similar_issues=[{"id": 2, "subject": "유사", "score": 0.5, "is_duplicate": False}],
            ai_summary="요약 내용",
            redmine_url="http://redmine.example.com",
            is_duplicate=False,
        )
        assert result is True
        mock_redmine.post_comment.assert_called_once()


@pytest.mark.asyncio
async def test_write_comment_prevents_duplicate_posting():
    """이미 Redmine Helper 댓글이 있으면 재작성 방지"""
    with patch("app.services.comment_writer.settings") as mock_settings:
        mock_settings.enable_auto_comment = True
        mock_redmine = MagicMock()
        mock_redmine.post_comment = AsyncMock()
        mock_redmine.get_issue = AsyncMock(
            return_value={"journals": [{"notes": "[Redmine Helper 자동 분석] 기존 댓글"}]}
        )

        writer = CommentWriter(redmine_client=mock_redmine)
        result = await writer.write_comment(
            issue_id=1,
            similar_issues=[],
            ai_summary=None,
            redmine_url="http://redmine.example.com",
            is_duplicate=False,
        )
        assert result is False
        mock_redmine.post_comment.assert_not_called()


@pytest.mark.asyncio
async def test_write_comment_force_update_skips_duplicate_check():
    """force=True (수동 재분석) 시 기존 댓글 있어도 작성"""
    with patch("app.services.comment_writer.settings") as mock_settings:
        mock_settings.enable_auto_comment = True
        mock_redmine = MagicMock()
        mock_redmine.post_comment = AsyncMock()
        mock_redmine.get_issue = AsyncMock(
            return_value={"journals": [{"notes": "[Redmine Helper 자동 분석] 기존 댓글"}]}
        )

        writer = CommentWriter(redmine_client=mock_redmine)
        result = await writer.write_comment(
            issue_id=1,
            similar_issues=[],
            ai_summary=None,
            redmine_url="http://redmine.example.com",
            is_duplicate=False,
            force=True,
        )
        assert result is True
        mock_redmine.post_comment.assert_called_once()
