import logging

from app.config import settings
from app.services.redmine_client import RedmineClient

logger = logging.getLogger(__name__)

COMMENT_HEADER = "[Redmine Helper 자동 분석]"


def build_comment_body(
    similar_issues: list[dict],
    ai_summary: str | None,
    redmine_url: str,
    is_duplicate: bool,
) -> str:
    """PRD 지정 댓글 형식으로 본문 생성."""
    lines = [f"## {COMMENT_HEADER}"]

    if is_duplicate:
        lines.append("")
        lines.append("⚠️ **중복 이슈 의심**: 아래 이슈와 내용이 매우 유사합니다. 중복 여부를 확인해주세요.")

    lines.append("")
    lines.append("### 해결 방법 요약")
    if ai_summary:
        lines.append(ai_summary)
    else:
        lines.append("_유사 이슈가 없거나 AI 요약을 생성할 수 없었습니다._")

    if similar_issues:
        lines.append("")
        lines.append("### 참고 이슈")
        base = redmine_url.rstrip("/")
        for issue in similar_issues:
            score_pct = int(issue.get("score", 0) * 100)
            dup_flag = " 🔴 중복 의심" if issue.get("is_duplicate") else ""
            lines.append(
                f"- [#{issue['id']} {issue['subject']}]({base}/issues/{issue['id']}) "
                f"(유사도 {score_pct}%){dup_flag}"
            )

    lines.append("")
    lines.append("---")
    lines.append("_이 댓글은 Redmine Helper가 자동으로 작성하였습니다._")
    return "\n".join(lines)


def _has_existing_comment(issue_detail: dict) -> bool:
    """이슈 상세 정보에서 기존 Redmine Helper 댓글 존재 여부 확인"""
    journals = issue_detail.get("journals", [])
    for journal in journals:
        notes = journal.get("notes", "")
        if COMMENT_HEADER in notes:
            return True
    return False


class CommentWriter:
    def __init__(self, redmine_client: RedmineClient = None):
        self.redmine = redmine_client or RedmineClient()

    async def write_comment(
        self,
        issue_id: int,
        similar_issues: list[dict],
        ai_summary: str | None,
        redmine_url: str,
        is_duplicate: bool,
        force: bool = False,
    ) -> bool:
        """
        Redmine 이슈에 분석 댓글 작성.

        Args:
            force: True이면 기존 댓글 존재 여부와 무관하게 작성 (수동 재분석용)

        Returns:
            True: 댓글 작성 완료
            False: 댓글 미작성 (플래그 비활성, 중복 방지, 에러)
        """
        # 플래그 확인 — ENABLE_AUTO_COMMENT=false(기본값)이면 작성하지 않음
        if not settings.enable_auto_comment:
            logger.info(
                f"[CommentWriter] 이슈 #{issue_id}: ENABLE_AUTO_COMMENT=false, 댓글 작성 건너뜀"
            )
            return False

        # 중복 방지 확인 (force=True이면 건너뜀)
        if not force:
            try:
                issue_detail = await self.redmine.get_issue(issue_id)
                if _has_existing_comment(issue_detail):
                    logger.info(
                        f"[CommentWriter] 이슈 #{issue_id}: 기존 댓글 존재, 재작성 방지"
                    )
                    return False
            except Exception as e:
                logger.warning(f"[CommentWriter] 이슈 #{issue_id} 상세 조회 실패: {e}")
                return False

        body = build_comment_body(
            similar_issues=similar_issues,
            ai_summary=ai_summary,
            redmine_url=redmine_url,
            is_duplicate=is_duplicate,
        )

        try:
            await self.redmine.post_comment(issue_id=issue_id, comment=body)
            logger.info(f"[CommentWriter] 이슈 #{issue_id}: 댓글 작성 완료")
            return True
        except Exception as e:
            logger.error(f"[CommentWriter] 이슈 #{issue_id}: 댓글 작성 실패 — {e}")
            return False
