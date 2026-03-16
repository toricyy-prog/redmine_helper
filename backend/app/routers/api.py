from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.analysis import AnalysisHistory, DuplicateDetection
from app.models.settings import AppSettings
from app.schemas.analysis import (
    AnalysisHistoryItem,
    AnalysisListResponse,
    DuplicateDetectionItem,
    RerunRequest,
    RerunResponse,
    StatsResponse,
)
from app.schemas.settings import SettingsResponse, SettingsUpdateRequest

router = APIRouter(prefix="/api", tags=["api"])


# ── 분석 이력 ───────────────────────────────────────────────────────────────

@router.get("/analysis", response_model=AnalysisListResponse)
async def list_analysis(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """최근 분석 이력 목록 (최대 100건, 페이지네이션)"""
    total = db.query(AnalysisHistory).count()
    items = (
        db.query(AnalysisHistory)
        .order_by(AnalysisHistory.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return AnalysisListResponse(
        items=[AnalysisHistoryItem.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/analysis/{analysis_id}", response_model=AnalysisHistoryItem)
async def get_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """분석 상세 조회 (원본 이슈 정보, 유사 이슈 목록, AI 요약)"""
    record = db.query(AnalysisHistory).filter(AnalysisHistory.id == analysis_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="분석 이력을 찾을 수 없습니다")
    return AnalysisHistoryItem.model_validate(record)


# ── 중복 감지 ────────────────────────────────────────────────────────────────

@router.get("/duplicates", response_model=List[DuplicateDetectionItem])
async def list_duplicates(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """중복 감지 이력 목록 (최신 순)"""
    items = (
        db.query(DuplicateDetection)
        .order_by(DuplicateDetection.created_at.desc())
        .limit(100)
        .all()
    )
    return [DuplicateDetectionItem.model_validate(item) for item in items]


# ── 통계 ─────────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """대시보드 통계: 카테고리별 이슈 수, 중복 감지 수, 성공/실패 통계"""
    total = db.query(AnalysisHistory).count()
    success = db.query(AnalysisHistory).filter(AnalysisHistory.status == "success").count()
    failed = db.query(AnalysisHistory).filter(AnalysisHistory.status == "failed").count()
    no_similar = db.query(AnalysisHistory).filter(AnalysisHistory.status == "no_similar").count()
    duplicates = db.query(DuplicateDetection).count()

    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_analyzed = db.query(AnalysisHistory).filter(
        AnalysisHistory.created_at >= today_start
    ).count()
    today_duplicates = db.query(DuplicateDetection).filter(
        DuplicateDetection.created_at >= today_start
    ).count()

    return StatsResponse(
        total_analyzed=total,
        total_success=success,
        total_failed=failed,
        total_no_similar=no_similar,
        total_duplicates=duplicates,
        success_rate=round(success / total, 2) if total > 0 else 0.0,
        today_analyzed=today_analyzed,
        today_duplicates=today_duplicates,
    )


# ── 재분석 ────────────────────────────────────────────────────────────────────

@router.post("/analysis/rerun", status_code=202, response_model=RerunResponse)
async def rerun_analysis(
    req: RerunRequest,
    background_tasks: BackgroundTasks,
    _: dict = Depends(get_current_user),
):
    """수동 재분석 실행 — 이슈 ID와 프로젝트 ID 지정"""
    background_tasks.add_task(_run_reanalysis, req.issue_id, req.project_id)
    return RerunResponse(
        status="accepted",
        message=f"이슈 #{req.issue_id} 재분석이 시작되었습니다",
    )


async def _run_reanalysis(issue_id: int, project_id: int):
    """재분석용 내부 함수 — Redmine에서 이슈 정보 조회 후 파이프라인 실행"""
    import logging

    from app.db.session import SessionLocal
    from app.models.analysis import AnalysisHistory
    from app.services.analysis_pipeline import run_analysis
    from app.services.redmine_client import RedmineClient

    _logger = logging.getLogger(__name__)
    try:
        client = RedmineClient()
        issue = await client.get_issue(issue_id)
        await run_analysis(
            issue_id=issue_id,
            project_id=project_id,
            subject=issue.get("subject", ""),
            description=issue.get("description", ""),
            force_comment=True,  # 기존 댓글 있어도 재작성
        )
    except Exception as e:
        _logger.error(f"[재분석 실패] 이슈 #{issue_id}: {e}")
        db = SessionLocal()
        try:
            record = AnalysisHistory(
                issue_id=issue_id,
                project_id=project_id,
                status="failed",
                error_message=f"RERUN_ERROR: {e}",
            )
            db.add(record)
            db.commit()
        except Exception as db_err:
            _logger.error(f"[재분석] DB 실패 기록 오류: {db_err}")
        finally:
            db.close()


# ── 설정 ─────────────────────────────────────────────────────────────────────

def _get_or_create_settings(db: Session) -> AppSettings:
    """설정 레코드가 없으면 기본값으로 생성"""
    s = db.query(AppSettings).first()
    if not s:
        s = AppSettings()
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """임계값, 카테고리 목록 조회"""
    s = _get_or_create_settings(db)
    return SettingsResponse(
        similarity_threshold=s.similarity_threshold,
        duplicate_threshold=s.duplicate_threshold,
        max_similar_issues=s.max_similar_issues,
        category_list=[c.strip() for c in s.category_list.split(",") if c.strip()],
        enable_auto_comment=bool(s.enable_auto_comment),
    )


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    req: SettingsUpdateRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """임계값, 카테고리 목록 수정 — 이후 분석에 즉시 반영"""
    s = _get_or_create_settings(db)
    if req.similarity_threshold is not None:
        s.similarity_threshold = req.similarity_threshold
    if req.duplicate_threshold is not None:
        s.duplicate_threshold = req.duplicate_threshold
    if req.max_similar_issues is not None:
        s.max_similar_issues = req.max_similar_issues
    if req.category_list is not None:
        s.category_list = ",".join(req.category_list)
    if req.enable_auto_comment is not None:
        s.enable_auto_comment = req.enable_auto_comment
    db.commit()
    db.refresh(s)
    return SettingsResponse(
        similarity_threshold=s.similarity_threshold,
        duplicate_threshold=s.duplicate_threshold,
        max_similar_issues=s.max_similar_issues,
        category_list=[c.strip() for c in s.category_list.split(",") if c.strip()],
        enable_auto_comment=bool(s.enable_auto_comment),
    )
