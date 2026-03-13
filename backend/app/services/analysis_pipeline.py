import logging

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.analysis import AnalysisHistory, DuplicateDetection
from app.services.redmine_client import RedmineClient
from app.services.similarity import SimilarityService

logger = logging.getLogger(__name__)


async def run_analysis(
    issue_id: int,
    project_id: int,
    subject: str,
    description: str,
    db: Session = None,
):
    """
    웹훅 수신 후 백그라운드에서 실행되는 분석 파이프라인.
    1. Redmine에서 기존 이슈 조회
    2. TF-IDF 유사도 계산
    3. DB에 결과 저장
    4. 로그 출력 (Sprint 2에서 댓글 작성으로 확장)
    """
    _db = db or SessionLocal()
    try:
        # 1. 기존 이슈 조회
        client = RedmineClient()
        existing_issues = await client.get_issues(project_id=project_id)
        # 현재 분석 대상 이슈 제외
        existing_issues = [i for i in existing_issues if i["id"] != issue_id]

        # 2. 유사도 계산
        similarity_svc = SimilarityService()
        new_issue = {"id": issue_id, "subject": subject, "description": description}
        similar = similarity_svc.find_similar(new_issue, existing_issues)

        # 3. 상태 결정
        status = "success" if similar else "no_similar"

        # 4. DB 저장
        record = AnalysisHistory(
            issue_id=issue_id,
            project_id=project_id,
            status=status,
            similar_issues=similar,
            ai_summary=None,
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

        # 5. 로그 출력
        logger.info(f"[분석 완료] 이슈 #{issue_id} — 유사 이슈 {len(similar)}건 발견")
        for item in similar:
            dup_flag = " [중복 의심]" if item["is_duplicate"] else ""
            logger.info(
                f"  - #{item['id']} {item['subject']} (유사도: {item['score']:.1%}){dup_flag}"
            )

        # 6. Redmine 댓글 자동 작성 (Sprint 2 구현 예정)
        # ⚠️  운영 안전을 위해 ENABLE_AUTO_COMMENT=true 로 명시 설정해야만 활성화됨
        # if settings.enable_auto_comment and similar:
        #     from app.services.comment_writer import write_comment
        #     await write_comment(issue_id=issue_id, similar=similar, ai_summary=record.ai_summary)

    except Exception as e:
        logger.error(f"[분석 실패] 이슈 #{issue_id}: {e}")
        error_record = AnalysisHistory(
            issue_id=issue_id,
            project_id=project_id,
            status="failed",
            error_message=str(e),
        )
        _db.add(error_record)
        _db.commit()
    finally:
        if db is None:
            _db.close()
