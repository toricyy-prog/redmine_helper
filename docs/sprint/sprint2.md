# Sprint 2 계획서 — Redmine Helper

> **For Claude:** REQUIRED SUB-SKILL: Use writing-plans skill to implement each task in this sprint.

**스프린트 번호**: Sprint 2
**기간**: 2026-03-27 (금) ~ 2026-04-09 (목) — 2주
**팀 규모**: 개발자 10명
**작성일**: 2026-03-13

---

## 스프린트 목표

> 유사 이슈 검색 결과를 Claude API로 요약하고 원본 이슈에 댓글을 자동 작성한다. 이슈 자동 분류도 동작한다.

**측정 가능한 성공 지표**:
- Redmine에 새 이슈를 등록하면 2분 이내에 AI 요약 댓글이 자동으로 작성된다.
- Claude API 호출 실패 시 유사 이슈 목록만 댓글로 작성된다.
- 이슈 등록 시 카테고리가 자동 분류되어 Redmine 커스텀 필드에 반영된다.
- 동일 이슈에 댓글 중복 작성이 발생하지 않는다.
- `ENABLE_AUTO_COMMENT=false` (기본값) 상태에서 댓글이 자동 작성되지 않는다.
- 통합 테스트: 웹훅 → 댓글 작성 전체 흐름 테스트 (pytest + httpx TestClient) 통과.

---

## 구현 범위

### 포함 항목 (In Scope)

| 분류 | 항목 |
|------|------|
| AI 클라이언트 | Claude API 클라이언트 구현 (`app/services/claude_client.py`) |
| 댓글 작성 | 댓글 자동 작성 서비스 (`app/services/comment_writer.py`), `ENABLE_AUTO_COMMENT` 플래그 제어 |
| 파이프라인 | 웹훅 → 검색 → AI 요약 → 댓글 작성 → DB 저장 전체 통합 |
| 에러 핸들링 | Claude API 실패, Redmine API 실패, 유사 이슈 없음 각 케이스 처리 |
| 이슈 분류 | 카테고리 분류 서비스 (`app/services/classifier.py`), 신뢰도 임계값 |
| Redmine 연동 | 커스텀 필드 업데이트 (분류 결과 반영) |
| 환경 설정 | `.env.example`에 `ENABLE_AUTO_COMMENT`, `CATEGORY_LIST`, `CLASSIFICATION_THRESHOLD` 추가 |

### 제외 항목 (Out of Scope)

| 항목 | 이유 |
|------|------|
| Vue.js 대시보드 | Sprint 3 범위 |
| 수동 재분석 API | Sprint 3 범위 (대시보드와 함께 구현) |
| 임베딩 기반 유사도 전환 | Sprint 2 PoC 후 Sprint 3 이후 결정 |
| 재시도 큐 (지수 백오프) | Sprint 4 범위 |
| WAL 모드 동시성 강화 | Sprint 4 범위 |

---

## 기술 스택 및 아키텍처

```
[Redmine] --webhook--> [FastAPI :8000]
                            |
                    BackgroundTasks
                            |
               ┌────────────┴──────────────────────┐
               │                                   │
    [Redmine API Client]              [Claude API Client]
    (httpx AsyncClient)               (anthropic SDK, async)
               │                                   │
               └────────────┬──────────────────────┘
                            │
               ┌────────────▼──────────────────────┐
               │      Analysis Pipeline             │
               │  1. get_issues (Redmine)           │
               │  2. find_similar (TF-IDF)          │
               │  3. summarize (Claude API)         │
               │  4. classify (Claude API)          │
               │  5. write_comment (조건부)          │
               │  6. update_custom_field (조건부)    │
               └────────────┬──────────────────────┘
                            │
                     [SQLite DB]
                 (analysis_history 업데이트)
```

**Sprint 2에서 추가되는 기술**:
- `anthropic` SDK (Claude API 비동기 호출)
- `ENABLE_AUTO_COMMENT` 환경 변수 (댓글 자동 작성 게이트)
- `CATEGORY_LIST` 환경 변수 (카테고리 목록, 쉼표 구분)
- `CLASSIFICATION_THRESHOLD` 환경 변수 (기본 0.7)

---

## 중요 제약사항

> **ENABLE_AUTO_COMMENT 플래그**
>
> - 기본값: `false` — 댓글 자동 작성 **비활성화**
> - `ENABLE_AUTO_COMMENT=true` 로 명시적 설정 시에만 댓글 작성 활성화
> - 댓글 작성 코드는 완전히 구현하되, 플래그 확인 로직으로 실행 여부를 결정
> - 이 원칙은 운영 안전을 위한 것으로, 어떠한 경우에도 변경하지 않는다

---

## 작업 분해 (Task Breakdown)

### Task 1: 환경 설정 및 의존성 추가

**우선순위**: Must Have | **예상 소요**: 0.5일 | **담당**: 인프라 담당 1명

**목표**: Sprint 2 신규 환경 변수 및 `anthropic` SDK 의존성 추가

**파일**:
- 수정: `.env.example`
- 수정: `backend/requirements.txt`
- 수정: `backend/app/config.py`

**세부 단계**:

**Step 1: `.env.example`에 Sprint 2 환경 변수 추가**
```bash
# Sprint 2 추가 항목
ENABLE_AUTO_COMMENT=false          # true로 설정 시에만 댓글 자동 작성 활성화
CATEGORY_LIST=버그,기능요청,문의,성능,보안   # 쉼표 구분 카테고리 목록
CLASSIFICATION_THRESHOLD=0.7       # 카테고리 분류 신뢰도 임계값 (0.0~1.0)
```

**Step 2: `backend/requirements.txt`에 `anthropic` SDK 추가**
```
anthropic==0.34.0
```

**Step 3: `backend/app/config.py`에 Sprint 2 설정 추가**
```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # ... 기존 설정 ...

    # Sprint 2 추가
    enable_auto_comment: bool = False          # 기본값: 댓글 자동 작성 비활성화
    category_list: str = "버그,기능요청,문의,성능,보안"
    classification_threshold: float = 0.7

    @property
    def categories(self) -> List[str]:
        return [c.strip() for c in self.category_list.split(",") if c.strip()]

    class Config:
        env_file = ".env"

settings = Settings()
```

**Step 4: Docker 이미지 재빌드**
```bash
docker compose build backend
docker compose up -d
```

**완료 기준**: `docker compose exec backend python -c "from app.config import settings; print(settings.enable_auto_comment)"` 결과가 `False`를 출력한다.

---

### Task 2: Claude API 클라이언트 구현

**우선순위**: Must Have | **예상 소요**: 1일 | **담당**: 백엔드 담당 2명

**목표**: `anthropic` SDK 기반 비동기 Claude API 클라이언트. 유사 이슈 정보를 받아 AI 요약을 반환한다.

**파일**:
- 생성: `backend/app/services/claude_client.py`
- 생성: `backend/tests/test_claude_client.py`

**세부 단계**:

**Step 1: 테스트 먼저 작성 (TDD)**
```python
# backend/tests/test_claude_client.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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
            similar_issues=similar_issues
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
            similar_issues=[{"id": 1, "subject": "유사", "score": 0.5, "comments": []}]
        )
        # 실패 시 None 반환 (요약 없이 이슈 목록만 댓글로 작성되도록)
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
            similar_issues=[]
        )
        assert result is None
        mock_client.messages.create.assert_not_called()

@pytest.mark.asyncio
async def test_prompt_truncates_to_2000_chars():
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
        similar_issues=similar_issues
    )
    # 전체 컨텍스트가 2000자 이내로 제한되어야 함
    assert len(prompt) <= 2500  # 시스템 프롬프트 포함 여유분
```

**Step 2: 테스트 실패 확인**
```bash
docker compose exec backend pytest tests/test_claude_client.py -v
# 예상: FAILED (모듈 없음)
```

**Step 3: `backend/app/services/claude_client.py` 구현**
```python
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
        similar_issues: list[dict]
    ) -> str:
        """
        2000자 이내의 프롬프트 구성.
        유사 이슈의 제목/댓글/유사도를 포함한다.
        """
        # 새 이슈 정보 (최대 500자)
        new_issue_text = f"새 이슈: {new_issue_subject}\n{new_issue_description[:300]}"

        # 유사 이슈 정보 (전체 합산 1500자 이내)
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
        similar_issues: list[dict]
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
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
            except Exception as e:
                if attempt == 0:
                    logger.warning(f"[Claude API] 1차 실패, 재시도 중: {e}")
                else:
                    logger.error(f"[Claude API] 최종 실패 (2회 시도): {e}")
                    return None
        return None
```

**Step 4: 테스트 통과 확인**
```bash
docker compose exec backend pytest tests/test_claude_client.py -v
# 예상: PASSED (4/4)
```

**Step 5: 커버리지 확인**
```bash
docker compose exec backend pytest tests/test_claude_client.py --cov=app/services/claude_client --cov-report=term-missing
```

**Step 6: 커밋**
```bash
git add backend/app/services/claude_client.py backend/tests/test_claude_client.py
git commit -m "feat: Claude API 클라이언트 구현 (비동기, 타임아웃 30초, 재시도 1회)"
```

**완료 기준**: 4개 단위 테스트 통과. API 실패 시 None 반환, 빈 유사 이슈 시 API 호출 없음.

---

### Task 3: 댓글 자동 작성 서비스 구현

**우선순위**: Must Have | **예상 소요**: 1.5일 | **담당**: 백엔드 담당 2명

**목표**: PRD 지정 형식의 댓글을 생성하고, `ENABLE_AUTO_COMMENT` 플래그가 `true`인 경우에만 Redmine에 작성한다. 중복 방지 로직 포함.

**파일**:
- 생성: `backend/app/services/comment_writer.py`
- 생성: `backend/tests/test_comment_writer.py`

**세부 단계**:

**Step 1: 테스트 먼저 작성 (TDD)**
```python
# backend/tests/test_comment_writer.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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
        is_duplicate=False
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
        is_duplicate=False
    )
    assert "[Redmine Helper 자동 분석]" in body
    assert "#1" in body
    assert "AI 요약을 생성할 수 없" in body  # 요약 없음 안내 문구

def test_build_comment_body_duplicate_warning():
    """중복 감지 시 경고 댓글 형식"""
    similar_issues = [{"id": 1, "subject": "동일 이슈", "score": 0.95, "is_duplicate": True}]
    body = build_comment_body(
        similar_issues=similar_issues,
        ai_summary=None,
        redmine_url="http://redmine.example.com",
        is_duplicate=True
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
        await writer.write_comment(
            issue_id=1,
            similar_issues=[],
            ai_summary=None,
            redmine_url="http://redmine.example.com",
            is_duplicate=False
        )
        # 플래그 비활성화 시 post_comment 호출 없음
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
        await writer.write_comment(
            issue_id=1,
            similar_issues=[{"id": 2, "subject": "유사", "score": 0.5, "is_duplicate": False}],
            ai_summary="요약 내용",
            redmine_url="http://redmine.example.com",
            is_duplicate=False
        )
        mock_redmine.post_comment.assert_called_once()

@pytest.mark.asyncio
async def test_write_comment_prevents_duplicate_posting():
    """이미 Redmine Helper 댓글이 있으면 재작성 방지"""
    with patch("app.services.comment_writer.settings") as mock_settings:
        mock_settings.enable_auto_comment = True
        mock_redmine = MagicMock()
        mock_redmine.post_comment = AsyncMock()
        # 기존에 Redmine Helper 댓글 존재
        mock_redmine.get_issue = AsyncMock(return_value={
            "journals": [{"notes": "[Redmine Helper 자동 분석] 기존 댓글"}]
        })

        writer = CommentWriter(redmine_client=mock_redmine)
        await writer.write_comment(
            issue_id=1,
            similar_issues=[],
            ai_summary=None,
            redmine_url="http://redmine.example.com",
            is_duplicate=False
        )
        # 중복 방지: post_comment 호출 없음
        mock_redmine.post_comment.assert_not_called()

@pytest.mark.asyncio
async def test_write_comment_force_update_skips_duplicate_check():
    """force=True (수동 재분석) 시 기존 댓글 있어도 작성"""
    with patch("app.services.comment_writer.settings") as mock_settings:
        mock_settings.enable_auto_comment = True
        mock_redmine = MagicMock()
        mock_redmine.post_comment = AsyncMock()
        mock_redmine.get_issue = AsyncMock(return_value={
            "journals": [{"notes": "[Redmine Helper 자동 분석] 기존 댓글"}]
        })

        writer = CommentWriter(redmine_client=mock_redmine)
        await writer.write_comment(
            issue_id=1,
            similar_issues=[],
            ai_summary=None,
            redmine_url="http://redmine.example.com",
            is_duplicate=False,
            force=True  # 수동 재분석 시
        )
        mock_redmine.post_comment.assert_called_once()
```

**Step 2: 테스트 실패 확인**
```bash
docker compose exec backend pytest tests/test_comment_writer.py -v
# 예상: FAILED (모듈 없음)
```

**Step 3: `backend/app/services/comment_writer.py` 구현**
```python
import logging
from app.config import settings
from app.services.redmine_client import RedmineClient

logger = logging.getLogger(__name__)

COMMENT_HEADER = "[Redmine Helper 자동 분석]"


def build_comment_body(
    similar_issues: list[dict],
    ai_summary: str | None,
    redmine_url: str,
    is_duplicate: bool
) -> str:
    """
    PRD 지정 댓글 형식으로 본문 생성.
    - 중복 감지 시: 경고 헤더 + 유사 이슈 링크
    - 일반: AI 요약 (없으면 안내 문구) + 참고 이슈 링크(유사도 % 포함)
    """
    lines = [f"## {COMMENT_HEADER}"]

    if is_duplicate:
        lines.append("")
        lines.append("⚠️ **중복 이슈 의심**: 아래 이슈와 내용이 매우 유사합니다. 중복 여부를 확인해주세요.")

    # AI 요약 섹션
    lines.append("")
    lines.append("### 해결 방법 요약")
    if ai_summary:
        lines.append(ai_summary)
    else:
        lines.append("_유사 이슈가 없거나 AI 요약을 생성할 수 없었습니다._")

    # 참고 이슈 링크 섹션
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
        force: bool = False
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
                # 조회 실패 시 안전하게 작성 생략
                return False

        # 댓글 본문 생성
        body = build_comment_body(
            similar_issues=similar_issues,
            ai_summary=ai_summary,
            redmine_url=redmine_url,
            is_duplicate=is_duplicate
        )

        # Redmine에 댓글 작성
        try:
            await self.redmine.post_comment(issue_id=issue_id, comment=body)
            logger.info(f"[CommentWriter] 이슈 #{issue_id}: 댓글 작성 완료")
            return True
        except Exception as e:
            logger.error(f"[CommentWriter] 이슈 #{issue_id}: 댓글 작성 실패 — {e}")
            return False
```

**Step 4: 테스트 통과 확인**
```bash
docker compose exec backend pytest tests/test_comment_writer.py -v
# 예상: PASSED (7/7)
```

**Step 5: 커밋**
```bash
git add backend/app/services/comment_writer.py backend/tests/test_comment_writer.py
git commit -m "feat: 댓글 자동 작성 서비스 구현 (ENABLE_AUTO_COMMENT 플래그, 중복 방지)"
```

**완료 기준**: 7개 단위 테스트 통과. `ENABLE_AUTO_COMMENT=false` 시 Redmine API 미호출, 기존 댓글 존재 시 재작성 방지 동작 확인.

---

### Task 4: 카테고리 분류 서비스 구현

**우선순위**: Should Have | **예상 소요**: 1일 | **담당**: 백엔드 담당 2명

**목표**: Claude API로 이슈를 카테고리로 분류한다. 신뢰도 임계값(0.7) 미만 시 분류 보류. 분류 결과를 Redmine 커스텀 필드에 업데이트한다.

**파일**:
- 생성: `backend/app/services/classifier.py`
- 수정: `backend/app/services/redmine_client.py` (커스텀 필드 업데이트 메서드 추가)
- 생성: `backend/tests/test_classifier.py`

**세부 단계**:

**Step 1: Redmine 클라이언트에 커스텀 필드 업데이트 메서드 추가**
```python
# backend/app/services/redmine_client.py 에 추가
async def update_custom_field(
    self,
    issue_id: int,
    custom_field_id: int,
    value: str
) -> None:
    """이슈 커스텀 필드 업데이트"""
    body = {
        "issue": {
            "custom_fields": [{"id": custom_field_id, "value": value}]
        }
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(2):
            try:
                r = await client.put(
                    f"{self.base_url}/issues/{issue_id}.json",
                    json=body,
                    headers=self.headers
                )
                r.raise_for_status()
                return
            except (httpx.HTTPError, httpx.TimeoutException):
                if attempt == 1:
                    raise
```

**Step 2: 테스트 먼저 작성 (TDD)**
```python
# backend/tests/test_classifier.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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
            threshold=0.7
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
            threshold=0.7
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
    mock_response.content = [MagicMock(text="분류할 수 없습니다.")]  # JSON 아님

    with patch("app.services.classifier.anthropic.AsyncAnthropic") as MockAnthropic:
        mock_client = MockAnthropic.return_value
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        from app.services.classifier import Classifier
        classifier = Classifier(api_key="test_key", categories=["버그"], threshold=0.7)
        result = await classifier.classify(subject="테스트", description="테스트")
        assert result is None
```

**Step 3: 테스트 실패 확인**
```bash
docker compose exec backend pytest tests/test_classifier.py -v
# 예상: FAILED (모듈 없음)
```

**Step 4: `backend/app/services/classifier.py` 구현**
```python
import json
import logging
import anthropic
from app.config import settings

logger = logging.getLogger(__name__)

CLASSIFIER_SYSTEM_PROMPT = """당신은 Redmine 이슈 분류 전문가입니다.
주어진 이슈를 제공된 카테고리 중 하나로 분류하고, 분류 신뢰도(0.0~1.0)를 반환합니다.
반드시 다음 JSON 형식으로만 응답하세요:
{"category": "카테고리명", "confidence": 0.85}"""


class Classifier:
    def __init__(
        self,
        api_key: str = None,
        categories: list[str] = None,
        threshold: float = None
    ):
        self.api_key = api_key or settings.claude_api_key
        self.categories = categories or settings.categories
        self.threshold = threshold if threshold is not None else settings.classification_threshold
        self._timeout = 30.0

    async def classify(self, subject: str, description: str) -> dict | None:
        """
        이슈를 카테고리로 분류.

        Returns:
            {"category": str, "confidence": float} — 신뢰도 임계값 이상인 경우
            None — 임계값 미만이거나 API 오류인 경우
        """
        categories_str = ", ".join(self.categories)
        prompt = (
            f"이슈 제목: {subject}\n"
            f"이슈 설명: {description[:500]}\n\n"
            f"가능한 카테고리: {categories_str}\n"
            f"위 카테고리 중 가장 적합한 것을 선택하고 신뢰도를 0.0~1.0으로 평가해주세요."
        )

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        try:
            response = await client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=128,
                timeout=self._timeout,
                system=CLASSIFIER_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = response.content[0].text.strip()

            # JSON 파싱
            result = json.loads(raw)
            category = result.get("category")
            confidence = float(result.get("confidence", 0.0))

            # 카테고리 유효성 확인
            if category not in self.categories:
                logger.warning(f"[Classifier] 유효하지 않은 카테고리 반환: {category}")
                return None

            # 신뢰도 임계값 확인
            if confidence < self.threshold:
                logger.info(
                    f"[Classifier] 신뢰도 미달 (confidence={confidence:.2f} < threshold={self.threshold}), "
                    f"분류 보류"
                )
                return None

            return {"category": category, "confidence": confidence}

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"[Classifier] 응답 파싱 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"[Classifier] API 호출 실패: {e}")
            return None
```

**Step 5: 테스트 통과 확인**
```bash
docker compose exec backend pytest tests/test_classifier.py -v
# 예상: PASSED (4/4)
```

**Step 6: 커밋**
```bash
git add backend/app/services/classifier.py backend/app/services/redmine_client.py backend/tests/test_classifier.py
git commit -m "feat: 카테고리 분류 서비스 구현 (Claude API, 신뢰도 임계값 0.7)"
```

**완료 기준**: 4개 단위 테스트 통과. 신뢰도 임계값 미만 및 API 실패 시 None 반환 확인.

---

### Task 5: 전체 파이프라인 통합

**우선순위**: Must Have | **예상 소요**: 1.5일 | **담당**: 백엔드 리드 1명 + 백엔드 담당 1명

**목표**: `analysis_pipeline.py`를 확장하여 유사도 검색 → Claude AI 요약 → 카테고리 분류 → 댓글 작성 → DB 저장 전체 흐름이 2분 이내 완료되도록 통합한다.

**파일**:
- 수정: `backend/app/services/analysis_pipeline.py`
- 수정: `backend/app/models/analysis.py` (ai_summary, category 필드 확인)
- 생성: `backend/tests/test_pipeline_integration.py`

**세부 단계**:

**Step 1: `analysis_history` 모델에 category 필드 추가**
```python
# backend/app/models/analysis.py 수정
class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, nullable=False, index=True)
    project_id = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False)  # success | failed | no_similar | comment_skipped
    similar_issues = Column(JSON, nullable=True)
    ai_summary = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)       # Sprint 2 추가
    category_confidence = Column(Float, nullable=True)  # Sprint 2 추가
    comment_written = Column(Integer, default=0)        # Sprint 2 추가 (0/1)
    created_at = Column(DateTime, default=datetime.utcnow)
    error_message = Column(Text, nullable=True)
```

**Step 2: Alembic 마이그레이션 추가**
```bash
docker compose exec backend alembic revision --autogenerate -m "add_category_and_comment_fields"
docker compose exec backend alembic upgrade head
```

**Step 3: 통합 테스트 먼저 작성**
```python
# backend/tests/test_pipeline_integration.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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

        mock_rc = MockRC.return_value
        mock_rc.get_issues = AsyncMock(return_value=mock_issues)

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
            issue_id=99,
            project_id=1,
            subject="로그인 페이지 오류",
            description="에러 발생",
            db=mock_db
        )

        # DB에 결과 저장 확인
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

        mock_rc = MockRC.return_value
        mock_rc.get_issues = AsyncMock(return_value=mock_issues)

        mock_sim = MockSim.return_value
        mock_sim.find_similar = MagicMock(return_value=mock_similar)

        # Claude API 실패 (None 반환)
        mock_claude = MockClaude.return_value
        mock_claude.summarize = AsyncMock(return_value=None)

        mock_classifier = MockClassifier.return_value
        mock_classifier.classify = AsyncMock(return_value=None)

        mock_writer = MockWriter.return_value
        mock_writer.write_comment = AsyncMock(return_value=True)

        mock_db = MagicMock()

        from app.services.analysis_pipeline import run_analysis
        await run_analysis(
            issue_id=99,
            project_id=1,
            subject="테스트 이슈",
            description="에러 발생",
            db=mock_db
        )

        # 요약 없이도 댓글 작성 시도 확인
        mock_writer.write_comment.assert_called_once()
        call_kwargs = mock_writer.write_comment.call_args.kwargs
        assert call_kwargs.get("ai_summary") is None  # AI 요약은 None
        assert call_kwargs.get("similar_issues") == mock_similar  # 유사 이슈는 전달

@pytest.mark.asyncio
async def test_full_pipeline_no_similar_issues():
    """유사 이슈 없을 때 status=no_similar로 DB 저장"""
    with patch("app.services.analysis_pipeline.RedmineClient") as MockRC, \
         patch("app.services.analysis_pipeline.SimilarityService") as MockSim, \
         patch("app.services.analysis_pipeline.ClaudeClient") as MockClaude, \
         patch("app.services.analysis_pipeline.Classifier") as MockClassifier, \
         patch("app.services.analysis_pipeline.CommentWriter") as MockWriter, \
         patch("app.services.analysis_pipeline.settings") as mock_settings:

        mock_settings.enable_auto_comment = True
        mock_settings.redmine_url = "http://redmine.test"

        mock_rc = MockRC.return_value
        mock_rc.get_issues = AsyncMock(return_value=[])

        mock_sim = MockSim.return_value
        mock_sim.find_similar = MagicMock(return_value=[])

        mock_claude = MockClaude.return_value
        mock_claude.summarize = AsyncMock()

        mock_classifier = MockClassifier.return_value
        mock_classifier.classify = AsyncMock(return_value=None)

        mock_writer = MockWriter.return_value

        mock_db = MagicMock()

        from app.services.analysis_pipeline import run_analysis
        await run_analysis(
            issue_id=99,
            project_id=1,
            subject="완전히 새로운 이슈",
            description="새 내용",
            db=mock_db
        )

        # Claude API 호출 없음 (유사 이슈 없으므로)
        mock_claude.summarize.assert_not_called()
        # DB 저장은 되어야 함
        assert mock_db.add.called
```

**Step 4: 테스트 실패 확인**
```bash
docker compose exec backend pytest tests/test_pipeline_integration.py -v
# 예상: FAILED (파이프라인 미구현)
```

**Step 5: `backend/app/services/analysis_pipeline.py` 확장**
```python
import logging
from sqlalchemy.orm import Session
from app.config import settings
from app.services.redmine_client import RedmineClient
from app.services.similarity import SimilarityService
from app.services.claude_client import ClaudeClient
from app.services.classifier import Classifier
from app.services.comment_writer import CommentWriter
from app.models.analysis import AnalysisHistory, DuplicateDetection
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


async def run_analysis(
    issue_id: int,
    project_id: int,
    subject: str,
    description: str,
    db: Session = None,
    force_comment: bool = False
):
    """
    전체 분석 파이프라인:
    1. Redmine에서 기존 이슈 조회
    2. TF-IDF 유사도 계산
    3. Claude API로 AI 요약 생성
    4. Claude API로 카테고리 분류
    5. 댓글 작성 (ENABLE_AUTO_COMMENT=true 시에만)
    6. DB 저장
    """
    _db = db or SessionLocal()
    try:
        # 1. 기존 이슈 조회
        client = RedmineClient()
        existing_issues = await client.get_issues(project_id=project_id)
        existing_issues = [i for i in existing_issues if i["id"] != issue_id]

        # 2. 유사도 계산
        similarity_svc = SimilarityService()
        new_issue = {"id": issue_id, "subject": subject, "description": description}
        similar = similarity_svc.find_similar(new_issue, existing_issues)
        is_duplicate = any(item["is_duplicate"] for item in similar)

        # 3. AI 요약 생성 (유사 이슈가 있을 때만)
        ai_summary = None
        if similar:
            # 유사 이슈의 저널(댓글) 정보 수집 (최대 3개 이슈)
            similar_with_comments = []
            for item in similar[:3]:
                try:
                    detail = await client.get_issue(item["id"])
                    comments = [
                        j.get("notes", "")
                        for j in detail.get("journals", [])
                        if j.get("notes", "").strip()
                    ]
                    similar_with_comments.append({**item, "comments": comments})
                except Exception:
                    similar_with_comments.append({**item, "comments": []})

            claude = ClaudeClient()
            ai_summary = await claude.summarize(
                new_issue_subject=subject,
                new_issue_description=description,
                similar_issues=similar_with_comments
            )

        # 4. 카테고리 분류
        category_result = None
        classifier = Classifier()
        category_result = await classifier.classify(subject=subject, description=description)

        # 5. 댓글 작성 (CommentWriter 내부에서 ENABLE_AUTO_COMMENT 플래그 확인)
        writer = CommentWriter(redmine_client=client)
        comment_written = await writer.write_comment(
            issue_id=issue_id,
            similar_issues=similar,
            ai_summary=ai_summary,
            redmine_url=settings.redmine_url,
            is_duplicate=is_duplicate,
            force=force_comment
        )

        # 6. 카테고리 커스텀 필드 업데이트 (분류 성공 시)
        if category_result and settings.enable_auto_comment:
            # REDMINE_CATEGORY_FIELD_ID 환경 변수로 커스텀 필드 ID 관리
            field_id = getattr(settings, "redmine_category_field_id", None)
            if field_id:
                try:
                    await client.update_custom_field(
                        issue_id=issue_id,
                        custom_field_id=int(field_id),
                        value=category_result["category"]
                    )
                except Exception as e:
                    logger.warning(f"[Pipeline] 커스텀 필드 업데이트 실패: {e}")

        # 상태 결정
        status = "success" if similar else "no_similar"

        # DB 저장
        record = AnalysisHistory(
            issue_id=issue_id,
            project_id=project_id,
            status=status,
            similar_issues=similar,
            ai_summary=ai_summary,
            category=category_result["category"] if category_result else None,
            category_confidence=category_result["confidence"] if category_result else None,
            comment_written=1 if comment_written else 0
        )
        _db.add(record)

        # 중복 감지 기록
        for item in similar:
            if item["is_duplicate"]:
                dup = DuplicateDetection(
                    source_issue_id=issue_id,
                    target_issue_id=item["id"],
                    similarity_score=item["score"]
                )
                _db.add(dup)

        _db.commit()

        logger.info(
            f"[Pipeline] 이슈 #{issue_id} 분석 완료 — "
            f"유사 {len(similar)}건, 요약={'있음' if ai_summary else '없음'}, "
            f"카테고리={category_result['category'] if category_result else 'N/A'}, "
            f"댓글={'작성' if comment_written else '미작성'}"
        )

    except Exception as e:
        logger.error(f"[Pipeline] 이슈 #{issue_id} 분석 실패: {e}")
        try:
            error_record = AnalysisHistory(
                issue_id=issue_id,
                project_id=project_id,
                status="failed",
                error_message=str(e)
            )
            _db.add(error_record)
            _db.commit()
        except Exception as db_err:
            logger.error(f"[Pipeline] DB 에러 기록 실패: {db_err}")
    finally:
        if db is None:
            _db.close()
```

**Step 6: 테스트 통과 확인**
```bash
docker compose exec backend pytest tests/test_pipeline_integration.py -v
# 예상: PASSED (3/3)
```

**Step 7: 전체 테스트 스위트 실행**
```bash
docker compose exec backend pytest --cov=app --cov-report=term-missing
# 목표: 커버리지 80% 이상
```

**Step 8: 커밋**
```bash
git add backend/app/services/analysis_pipeline.py backend/app/models/analysis.py \
        backend/alembic/versions/ backend/tests/test_pipeline_integration.py
git commit -m "feat: 전체 분석 파이프라인 통합 (AI 요약 + 분류 + 댓글 작성)"
```

**완료 기준**: 3개 통합 테스트 통과. `ENABLE_AUTO_COMMENT=false` 시 댓글 미작성 확인, Claude API 실패 시 이슈 목록만 댓글 작성 확인.

---

### Task 6: 에러 핸들링 강화

**우선순위**: Must Have | **예상 소요**: 1일 | **담당**: 백엔드 담당 2명

**목표**: Claude API 실패, Redmine API 실패, 유사 이슈 없음, 타임아웃 각 케이스를 명확히 처리하고 DB에 에러 상태를 기록한다.

**파일**:
- 생성: `backend/app/exceptions.py`
- 수정: `backend/app/services/analysis_pipeline.py`
- 생성: `backend/tests/test_error_handling.py`

**세부 단계**:

**Step 1: `backend/app/exceptions.py` 작성**
```python
class RedmineHelperError(Exception):
    """기본 에러 클래스"""
    pass

class RedmineAPIError(RedmineHelperError):
    """Redmine API 호출 실패"""
    error_code = "REDMINE_API_ERROR"

class ClaudeAPIError(RedmineHelperError):
    """Claude API 호출 실패"""
    error_code = "CLAUDE_API_ERROR"

class NoSimilarIssuesError(RedmineHelperError):
    """유사 이슈 없음 (에러가 아닌 정상 상태)"""
    error_code = "NO_SIMILAR_ISSUES"

class WebhookValidationError(RedmineHelperError):
    """웹훅 검증 실패"""
    error_code = "WEBHOOK_VALIDATION_ERROR"
```

**Step 2: 테스트 먼저 작성**
```python
# backend/tests/test_error_handling.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

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
            issue_id=1,
            project_id=1,
            subject="테스트",
            description="테스트",
            db=mock_db
        )

        # DB에 failed 상태 기록 확인
        assert mock_db.add.called
        record = mock_db.add.call_args[0][0]
        assert record.status == "failed"
        assert record.error_message is not None

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

        mock_rc = MockRC.return_value
        mock_rc.get_issues = AsyncMock(return_value=mock_issues)
        mock_rc.get_issue = AsyncMock(return_value={"journals": []})

        mock_sim = MockSim.return_value
        mock_sim.find_similar = MagicMock(return_value=mock_similar)

        mock_claude = MockClaude.return_value
        mock_claude.summarize = AsyncMock(return_value="AI 요약")

        mock_classifier = MockClassifier.return_value
        mock_classifier.classify = AsyncMock(return_value=None)

        # 댓글 작성 실패
        mock_writer = MockWriter.return_value
        mock_writer.write_comment = AsyncMock(return_value=False)

        mock_db = MagicMock()

        from app.services.analysis_pipeline import run_analysis
        await run_analysis(
            issue_id=99, project_id=1,
            subject="테스트", description="테스트",
            db=mock_db
        )

        # 댓글 실패해도 DB 저장은 성공
        assert mock_db.add.called
        assert mock_db.commit.called
        record = mock_db.add.call_args[0][0]
        assert record.status == "success"
        assert record.comment_written == 0  # 댓글 미작성 기록
```

**Step 3: 테스트 실패 확인**
```bash
docker compose exec backend pytest tests/test_error_handling.py -v
# 예상: FAILED (에러 처리 미구현)
```

**Step 4: `analysis_pipeline.py`에 에러 코드 기록 강화**

파이프라인의 `except` 블록을 다음과 같이 강화:
```python
except httpx.HTTPError as e:
    error_msg = f"REDMINE_API_ERROR: {e}"
    logger.error(f"[Pipeline] 이슈 #{issue_id} Redmine API 실패: {e}")
    # ... DB 기록 ...
except Exception as e:
    error_msg = f"UNKNOWN_ERROR: {e}"
    logger.error(f"[Pipeline] 이슈 #{issue_id} 예상치 못한 오류: {e}")
    # ... DB 기록 ...
```

**Step 5: 테스트 통과 확인**
```bash
docker compose exec backend pytest tests/test_error_handling.py -v
# 예상: PASSED (2/2)
```

**Step 6: 커밋**
```bash
git add backend/app/exceptions.py backend/app/services/analysis_pipeline.py \
        backend/tests/test_error_handling.py
git commit -m "feat: 에러 핸들링 강화 (에러 코드 분류, DB 상태 기록)"
```

**완료 기준**: Redmine API 실패, 댓글 작성 실패 각각 DB에 올바른 상태가 기록된다.

---

### Task 7: E2E 통합 검증

**우선순위**: Must Have | **예상 소요**: 0.5일 | **담당**: QA 1명 + 백엔드 1명

**목표**: `docker compose up` 후 실제 웹훅 요청으로 Sprint 2 전체 흐름 동작 확인

**세부 단계**:

**Step 1: 서비스 재빌드 및 마이그레이션**
```bash
docker compose up --build -d
docker compose exec backend alembic upgrade head
```

**Step 2: ENABLE_AUTO_COMMENT=false (기본값) 상태 검증**
```bash
# .env에 ENABLE_AUTO_COMMENT=false (또는 미설정) 확인 후 웹훅 전송
SECRET="your_webhook_secret"
PAYLOAD='{"action":"opened","issue":{"id":999,"subject":"로그인 500 오류 재발","description":"로그인 시 500 에러가 또 발생합니다.","project":{"id":1,"name":"테스트"}}}'
SIG=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')
curl -X POST http://localhost:8000/webhook/redmine \
  -H "Content-Type: application/json" \
  -H "X-Redmine-Token: $SIG" \
  -d "$PAYLOAD"

# 로그에서 "ENABLE_AUTO_COMMENT=false, 댓글 작성 건너뜀" 확인
docker compose logs backend | grep "건너뜀"
```

**Step 3: 전체 테스트 스위트 최종 실행**
```bash
docker compose exec backend pytest --cov=app --cov-report=term-missing -v
# 목표: 전체 커밋 80% 이상, 전체 테스트 통과
```

**Step 4: DB 상태 확인**
```bash
docker compose exec backend python -c "
from app.db.session import SessionLocal
from app.models.analysis import AnalysisHistory
db = SessionLocal()
records = db.query(AnalysisHistory).order_by(AnalysisHistory.id.desc()).limit(5).all()
for r in records:
    print(f'#{r.issue_id} status={r.status} category={r.category} comment={r.comment_written}')
"
```

**Step 5: 최종 커밋**
```bash
git add .
git commit -m "chore: Sprint 2 E2E 검증 완료"
```

**완료 기준**: Sprint 2 Definition of Done 전체 항목 충족.

---

## 의존성 및 리스크

### 태스크 간 의존성

```
Task 1 (환경 설정)
    ├── Task 2 (Claude API 클라이언트)
    │       └── Task 4 (카테고리 분류 서비스)
    ├── Task 3 (댓글 자동 작성 서비스)
    └── Task 5 (전체 파이프라인 통합) ← Task 2, 3, 4 완료 필요
            └── Task 6 (에러 핸들링 강화) ← Task 5 완료 필요
                    └── Task 7 (E2E 검증) ← Task 6 완료 필요
```

### 리스크 및 대응 방안

| 리스크 | 가능성 | 영향도 | 대응 방안 |
|--------|--------|--------|-----------|
| Claude API 응답 지연/장애 | 낮음 | 중간 | 타임아웃 30초, 실패 시 None 반환 → 이슈 목록만 댓글 작성 |
| Claude API 요금 초과 | 중간 | 중간 | 이슈 내용 2000자 제한, 유사 이슈 댓글 최대 3개만 포함 |
| Redmine 커스텀 필드 ID 미확인 | 높음 | 낮음 | `REDMINE_CATEGORY_FIELD_ID` 미설정 시 커스텀 필드 업데이트 건너뜀 |
| 카테고리 분류 오분류 | 중간 | 낮음 | 신뢰도 임계값 0.7, 미달 시 분류 보류 (대시보드에서 수동 검토 — Sprint 3) |
| 중복 댓글 방지 실패 (동시 웹훅) | 낮음 | 높음 | DB 트랜잭션 수준 락은 Sprint 4에서 강화, Sprint 2에서는 단일 요청 기준 방지 |

### 사전 준비 사항 (착수 전 확인 필요)

- ⬜ Claude API Key 발급 및 `.env`에 `CLAUDE_API_KEY` 등록
- ⬜ TF-IDF 유사도 품질 평가 완료 (Sprint 1 결과 기반)
- ⬜ Redmine 커스텀 필드 목록 확인 및 `REDMINE_CATEGORY_FIELD_ID` 결정
- ⬜ 댓글 작성 형식 최종 확정 (PRD 4.2 기준)
- ⬜ `ENABLE_AUTO_COMMENT` 운영 활성화 시점 팀 합의

---

## 팀 역할 분담 (10명 기준)

| 역할 | 인원 | 담당 태스크 |
|------|------|-------------|
| 인프라 담당 | 1명 | Task 1 (환경 설정) |
| 백엔드 리드 | 1명 | Task 5 (파이프라인 통합), Task 6 (에러 핸들링) |
| 백엔드 개발 | 4명 | Task 2 (Claude 클라이언트), Task 3 (댓글 서비스), Task 4 (분류 서비스) — 2명씩 페어 |
| 백엔드 개발 | 1명 | Task 6 (에러 핸들링) 보조 |
| QA | 1명 | Task 7 (E2E 검증), 전체 테스트 리뷰 |
| PM/아키텍트 | 2명 | 코드 리뷰, 스프린트 진행 관리, Sprint 3 준비 |

---

## 완료 기준 (Definition of Done)

| # | 항목 | 확인 방법 |
|---|------|-----------|
| 1 | ⬜ Redmine 새 이슈 등록 시 2분 이내 AI 요약 댓글 자동 작성 (`ENABLE_AUTO_COMMENT=true` 시) | E2E 테스트 (Task 7) |
| 2 | ⬜ Claude API 호출 실패 시 유사 이슈 목록만 댓글 작성 | `test_full_pipeline_claude_failure_fallback` |
| 3 | ⬜ 이슈 등록 시 카테고리 자동 분류 → Redmine 커스텀 필드 반영 | E2E 테스트 |
| 4 | ⬜ 동일 이슈에 댓글 중복 작성 없음 | `test_write_comment_prevents_duplicate_posting` |
| 5 | ⬜ `ENABLE_AUTO_COMMENT=false` (기본값) 시 Redmine 댓글 미작성 | `test_write_comment_disabled_by_flag` |
| 6 | ⬜ 전체 단위/통합 테스트 커버리지 80% 이상 | `pytest --cov` 결과 |
| 7 | ⬜ 에러 케이스별 DB 상태 기록 (failed + error_message) | `test_pipeline_redmine_api_failure` |

---

## 예상 산출물

| 산출물 | 경로 | 설명 |
|--------|------|------|
| Claude API 클라이언트 | `backend/app/services/claude_client.py` | 비동기, 타임아웃 30초, 재시도 1회 |
| 댓글 작성 서비스 | `backend/app/services/comment_writer.py` | PRD 형식, 중복 방지, ENABLE_AUTO_COMMENT 제어 |
| 카테고리 분류 서비스 | `backend/app/services/classifier.py` | Claude API, 신뢰도 임계값 0.7 |
| 파이프라인 통합 | `backend/app/services/analysis_pipeline.py` | 전체 흐름 통합 (Sprint 1 확장) |
| 에러 정의 | `backend/app/exceptions.py` | 에러 코드 분류 |
| DB 마이그레이션 | `backend/alembic/versions/` | category, comment_written 필드 추가 |
| 단위 테스트 | `backend/tests/test_claude_client.py` | Claude 클라이언트 4개 테스트 |
| 단위 테스트 | `backend/tests/test_comment_writer.py` | 댓글 서비스 7개 테스트 |
| 단위 테스트 | `backend/tests/test_classifier.py` | 분류 서비스 4개 테스트 |
| 통합 테스트 | `backend/tests/test_pipeline_integration.py` | 파이프라인 통합 3개 테스트 |
| 에러 테스트 | `backend/tests/test_error_handling.py` | 에러 처리 2개 테스트 |

---

## 다음 스프린트 준비 사항

Sprint 2 완료 후 Sprint 3 착수 전 확인해야 할 사항:

- ⬜ 임베딩 방식 PoC 결과 검토 (Sprint 2 리뷰에서 채택 여부 결정)
- ⬜ 분석 이력 REST API 설계 (`GET /api/analysis`, `GET /api/stats` 등)
- ⬜ Vue.js 프론트엔드 개발 환경 준비 (Node.js, Vite)
- ⬜ 대시보드 UI/UX 설계 (와이어프레임)
- ⬜ `ENABLE_AUTO_COMMENT=true` 운영 활성화 시점 및 책임자 결정
