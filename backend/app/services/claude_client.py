import logging

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 Redmine 이슈 분석 전문가입니다.
새 이슈와 유사한 기존 이슈들의 해결 방법을 분석하여 간결하고 실용적인 요약을 작성합니다.
응답은 반드시 한국어로 작성하고, 마크다운 형식을 사용합니다."""


class ClaudeClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.claude_api_key
        self._timeout = 30.0

    def _build_prompt(
        self,
        new_issue_subject: str,
        new_issue_description: str,
        similar_issues: list[dict],
    ) -> str:
        """2000자 이내의 프롬프트 구성."""
        new_issue_text = f"새 이슈: {new_issue_subject}\n{new_issue_description[:300]}"

        similar_text_parts = []
        budget = 1500
        for issue in similar_issues:
            score_pct = int(issue.get("score", 0) * 100)
            comments = issue.get("comments", [])
            comment_preview = " / ".join(c[:100] for c in comments[:3])
            part = (
                f"[유사도 {score_pct}%] #{issue['id']} {issue['subject']}\n"
                f"  해결 힌트: {comment_preview}"
            )
            if budget - len(part) < 0:
                break
            similar_text_parts.append(part)
            budget -= len(part)

        similar_text = "\n".join(similar_text_parts)
        return (
            f"{new_issue_text}\n\n"
            f"## 유사 이슈 목록\n{similar_text}\n\n"
            f"위 유사 이슈들을 참고하여 새 이슈 해결에 도움이 될 요약을 작성해주세요. "
            f"해결 방법 위주로 간결하게 (300자 이내)."
        )

    async def summarize(
        self,
        new_issue_subject: str,
        new_issue_description: str,
        similar_issues: list[dict],
    ) -> str | None:
        """
        유사 이슈 정보를 바탕으로 AI 요약 생성.
        실패 시 1회 재시도, 그래도 실패하면 None 반환.
        """
        if not similar_issues:
            return None

        prompt = self._build_prompt(new_issue_subject, new_issue_description, similar_issues)
        client = anthropic.AsyncAnthropic(api_key=self.api_key)

        for attempt in range(2):
            try:
                response = await client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=512,
                    timeout=self._timeout,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text
            except Exception as e:
                if attempt == 0:
                    logger.warning(f"[Claude API] 1차 실패, 재시도 중: {e}")
                else:
                    logger.error(f"[Claude API] 최종 실패 (2회 시도): {e}")
                    return None
        return None
