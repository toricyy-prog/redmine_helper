import asyncio
import logging

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import SessionLocal
from app.models.analysis import AnalysisHistory, DuplicateDetection
from app.services.classifier import Classifier
from app.services.claude_client import ClaudeClient
from app.services.comment_writer import CommentWriter
from app.services.redmine_client import RedmineClient
from app.services.similarity import SimilarityService

logger = logging.getLogger(__name__)

# 이슈별 동시 처리 방지용 락
_issue_locks: dict[int, asyncio.Lock] = {}
_locks_mutex = asyncio.Lock()


async def _get_issue_lock(issue_id: int) -> asyncio.Lock:
    """이슈 ID별 asyncio.Lock 반환 (없으면 신규 생성)"""
    async with _locks_mutex:
        if issue_id not in _issue_locks:
            _issue_locks[issue_id] = asyncio.Lock()
        return _issue_locks[issue_id]


async def run_analysis(
    issue_id: int,
    project_id: int,
    subject: str,
    description: str,
    db: Session = None,
    force_comment: bool = False,
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
    lock = await _get_issue_lock(issue_id)
    async with lock:
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
                    similar_issues=similar_with_comments,
                )

            # 4. 카테고리 분류
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
                force=force_comment,
            )

            # 6. 카테고리 커스텀 필드 업데이트 (분류 성공 + 자동 댓글 활성화 시)
            if category_result and settings.enable_auto_comment and settings.redmine_category_field_id:
                try:
                    await client.update_custom_field(
                        issue_id=issue_id,
                        custom_field_id=int(settings.redmine_category_field_id),
                        value=category_result["category"],
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
                comment_written=1 if comment_written else 0,
            )
            _db.add(record)

            # 중복 감지 기록
            for item in similar:
                if item["is_duplicate"]:
                    dup = DuplicateDetection(
                        source_issue_id=issue_id,
                        target_issue_id=item["id"],
                        similarity_score=item["score"],
                    )
                    _db.add(dup)

            _db.commit()

            logger.info(
                f"[Pipeline] 이슈 #{issue_id} 분석 완료 — "
                f"유사 {len(similar)}건, 요약={'있음' if ai_summary else '없음'}, "
                f"카테고리={category_result['category'] if category_result else 'N/A'}, "
                f"댓글={'작성' if comment_written else '미작성'}"
            )

        except httpx.HTTPError as e:
            error_msg = f"REDMINE_API_ERROR: {e}"
            logger.error(f"[Pipeline] 이슈 #{issue_id} Redmine API 실패: {e}")
            _save_error(_db, issue_id, project_id, error_msg)
        except Exception as e:
            error_msg = f"UNKNOWN_ERROR: {e}"
            logger.error(f"[Pipeline] 이슈 #{issue_id} 예상치 못한 오류: {e}")
            _save_error(_db, issue_id, project_id, error_msg)
        finally:
            if db is None:
                _db.close()


def _save_error(db: Session, issue_id: int, project_id: int, error_message: str) -> None:
    """에러 발생 시 DB에 실패 기록 저장"""
    try:
        record = AnalysisHistory(
            issue_id=issue_id,
            project_id=project_id,
            status="failed",
            error_message=error_message,
        )
        db.add(record)
        db.commit()
    except Exception as db_err:
        logger.error(f"[Pipeline] DB 에러 기록 실패: {db_err}")
