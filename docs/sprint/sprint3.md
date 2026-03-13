# Sprint 3 계획서 — Redmine Helper

> **For Claude:** REQUIRED SUB-SKILL: Use writing-plans skill to implement each task in this sprint.

**스프린트 번호**: Sprint 3
**기간**: 2026-04-10 (금) ~ 2026-04-23 (목) — 2주
**팀 규모**: 개발자 10명
**작성일**: 2026-03-13

---

## 스프린트 목표

> 팀원이 브라우저에서 분석 이력, 중복 감지 이력, 통계, 설정을 확인하고 수동 재분석을 실행할 수 있는 Vue.js 대시보드를 제공한다.

**측정 가능한 성공 지표**:
- `docker compose up` 후 `http://localhost:8080` 접속 시 로그인 화면이 표시된다.
- 로그인 후 대시보드 홈에서 최근 100건의 분석 이력을 확인할 수 있다.
- 분석 상세 화면에서 원본 이슈 링크, 유사 이슈 목록, AI 요약이 표시된다.
- 수동 재분석 버튼 클릭 시 재분석이 실행되고 결과가 갱신된다.
- 설정 화면에서 임계값 변경 후 저장하면 이후 분석에 적용된다.
- 백엔드 API 전체 단위 테스트 통과 (pytest).

---

## 구현 범위

### 포함 항목 (In Scope)

| 분류 | 항목 |
|------|------|
| 백엔드 API | `GET /api/analysis`, `GET /api/analysis/{id}`, `GET /api/duplicates`, `GET /api/stats` |
| 백엔드 API | `POST /api/analysis/rerun`, `GET /api/settings`, `PUT /api/settings` |
| 인증 | `DASHBOARD_PASSWORD` 기반 Bearer 토큰 인증 미들웨어 |
| 프론트엔드 초기화 | Vue.js 3 + Vite + Vue Router + Pinia + Axios 프로젝트 (`frontend/`) |
| 프론트엔드 화면 | 로그인 (`/login`), 대시보드 홈 (`/`), 분석 상세 (`/analysis/:id`) |
| 프론트엔드 화면 | 중복 감지 목록 (`/duplicates`), 설정 (`/settings`) |
| 빌드 통합 | Docker 빌드 시 Vue.js 정적 파일 → FastAPI `static/` 서빙 |
| 비기능 | 반응형 레이아웃 (최소 1280px 기준) |

### 제외 항목 (Out of Scope)

| 항목 | 이유 |
|------|------|
| 임베딩 기반 유사도 전환 | Sprint 4 백로그 |
| 재시도 큐 (지수 백오프) | Sprint 4 범위 |
| WAL 모드 동시성 강화 | Sprint 4 범위 |
| 헬스체크 엔드포인트 상세 | Sprint 4 범위 |
| 모바일 반응형 | 팀 내부 도구, 데스크탑만 지원 |

---

## 기술 스택 및 아키텍처

```
[브라우저] --HTTP--> [FastAPI :8080]
                         |
              ┌──────────┴──────────────┐
              │                         │
    [Vue.js SPA 정적 파일]      [REST API 라우터]
    (FastAPI static/ 서빙)          /api/*
                                     |
                          ┌──────────┴───────────┐
                          │                       │
               [Auth Middleware]        [API Handlers]
               (Bearer 토큰 검증)    analysis, duplicates,
                                     stats, settings, rerun
                                          |
                                    [SQLite DB]
                             (analysis_history, duplicate_detections,
                              app_settings)
```

**Sprint 3에서 추가되는 기술**:
- Vue.js 3 (Composition API, `<script setup>`)
- Vite (빌드 도구)
- Vue Router 4 (클라이언트 사이드 라우팅)
- Pinia (상태 관리)
- Axios (HTTP 클라이언트)
- python-jose (JWT 발급/검증)
- markdown-it (AI 요약 마크다운 렌더링)

---

## 작업 분해 (Task Breakdown)

### Task 1: 백엔드 — 대시보드 인증 미들웨어 구현

**우선순위**: Must Have | **예상 소요**: 0.5일 | **담당**: 백엔드 담당 1명

**목표**: `DASHBOARD_PASSWORD` 기반 로그인 → JWT 발급 → Bearer 토큰 검증 미들웨어

**파일**:
- 생성: `backend/app/routers/auth.py`
- 생성: `backend/app/dependencies/auth.py`
- 수정: `backend/app/config.py` (JWT_SECRET_KEY 추가)
- 수정: `backend/app/main.py` (auth 라우터 등록)
- 생성: `backend/tests/test_auth.py`

**세부 단계**:

**Step 1: `backend/app/config.py` 수정 — JWT 설정 추가**
```python
class Settings(BaseSettings):
    # ... 기존 설정 ...
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24시간
```

**Step 2: 테스트 먼저 작성 (TDD)**
```python
# backend/tests/test_auth.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_login_success(monkeypatch):
    """올바른 비밀번호로 로그인 시 JWT 반환"""
    monkeypatch.setenv("DASHBOARD_PASSWORD", "secret123")
    response = client.post("/api/auth/login", json={"password": "secret123"})
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_wrong_password(monkeypatch):
    """잘못된 비밀번호로 로그인 시 401 반환"""
    monkeypatch.setenv("DASHBOARD_PASSWORD", "secret123")
    response = client.post("/api/auth/login", json={"password": "wrong"})
    assert response.status_code == 401

def test_protected_endpoint_without_token():
    """토큰 없이 보호된 엔드포인트 접근 시 401"""
    response = client.get("/api/analysis")
    assert response.status_code == 401

def test_protected_endpoint_with_valid_token(monkeypatch):
    """유효한 토큰으로 보호된 엔드포인트 접근 시 200"""
    monkeypatch.setenv("DASHBOARD_PASSWORD", "secret123")
    login_resp = client.post("/api/auth/login", json={"password": "secret123"})
    token = login_resp.json()["access_token"]
    response = client.get("/api/analysis", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
```

**Step 3: 테스트 실패 확인**
```bash
docker compose exec backend pytest tests/test_auth.py -v
# 예상: FAILED (엔드포인트 없음)
```

**Step 4: `backend/app/routers/auth.py` 구현**
```python
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from jose import jwt
from pydantic import BaseModel
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

def create_access_token() -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": "dashboard", "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    if req.password != settings.dashboard_password:
        raise HTTPException(status_code=401, detail="비밀번호가 올바르지 않습니다")
    return TokenResponse(access_token=create_access_token())
```

**Step 5: `backend/app/dependencies/auth.py` 구현**
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.config import settings

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """JWT 토큰 검증 의존성 — 모든 보호된 API에 주입"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        if payload.get("sub") != "dashboard":
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="토큰이 만료되었거나 유효하지 않습니다")
```

**Step 6: `requirements.txt`에 의존성 추가**
```
python-jose[cryptography]==3.3.0
```

**Step 7: 테스트 통과 확인**
```bash
docker compose exec backend pytest tests/test_auth.py -v
# 예상: PASSED (4/4)
```

**Step 8: 커밋**
```bash
git add backend/app/routers/auth.py backend/app/dependencies/ backend/tests/test_auth.py
git commit -m "feat: DASHBOARD_PASSWORD 기반 JWT 인증 미들웨어 구현"
```

**완료 기준**: 올바른 비밀번호 → JWT 발급, 잘못된 비밀번호 → 401, 토큰 없는 API 접근 → 401.

---

### Task 2: 백엔드 — 분석 이력 API 구현 (`GET /api/analysis`, `GET /api/analysis/{id}`)

**우선순위**: Must Have | **예상 소요**: 1일 | **담당**: 백엔드 담당 2명

**목표**: 분석 이력 목록(페이지네이션) 및 상세 조회 API

**파일**:
- 생성: `backend/app/routers/api.py`
- 생성: `backend/app/schemas/analysis.py`
- 생성: `backend/tests/test_api_analysis.py`

**세부 단계**:

**Step 1: `backend/app/schemas/analysis.py` 작성**
```python
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class SimilarIssueItem(BaseModel):
    id: int
    subject: str
    score: float
    is_duplicate: bool

class AnalysisHistoryItem(BaseModel):
    id: int
    issue_id: int
    project_id: int
    status: str  # success | failed | no_similar
    similar_issues: Optional[List[SimilarIssueItem]] = None
    ai_summary: Optional[str] = None
    created_at: datetime
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

class AnalysisListResponse(BaseModel):
    items: List[AnalysisHistoryItem]
    total: int
    page: int
    page_size: int
```

**Step 2: 테스트 먼저 작성 (TDD)**
```python
# backend/tests/test_api_analysis.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.session import Base, get_db
from app.models.analysis import AnalysisHistory
from app.dependencies.auth import get_current_user
from datetime import datetime

# 테스트용 인메모리 DB 설정
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def override_get_current_user():
    return {"sub": "dashboard"}

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_get_analysis_list_empty():
    """분석 이력이 없을 때 빈 목록 반환"""
    response = client.get("/api/analysis")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0

def test_get_analysis_list_with_data():
    """분석 이력이 있을 때 목록 반환"""
    db = TestingSessionLocal()
    record = AnalysisHistory(
        issue_id=1, project_id=1, status="success",
        similar_issues=[{"id": 2, "subject": "유사 이슈", "score": 0.8, "is_duplicate": False}],
        ai_summary="요약 내용", created_at=datetime.utcnow()
    )
    db.add(record)
    db.commit()
    db.close()

    response = client.get("/api/analysis")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["issue_id"] == 1

def test_get_analysis_detail():
    """분석 상세 조회"""
    db = TestingSessionLocal()
    record = AnalysisHistory(
        issue_id=5, project_id=2, status="success",
        similar_issues=[{"id": 3, "subject": "테스트", "score": 0.75, "is_duplicate": False}],
        ai_summary="AI 요약 텍스트", created_at=datetime.utcnow()
    )
    db.add(record)
    db.commit()
    record_id = record.id
    db.close()

    response = client.get(f"/api/analysis/{record_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["issue_id"] == 5
    assert data["ai_summary"] == "AI 요약 텍스트"

def test_get_analysis_detail_not_found():
    """존재하지 않는 분석 ID 조회 시 404"""
    response = client.get("/api/analysis/99999")
    assert response.status_code == 404

def test_get_analysis_pagination():
    """페이지네이션 동작 확인"""
    db = TestingSessionLocal()
    for i in range(10):
        db.add(AnalysisHistory(issue_id=i, project_id=1, status="success", created_at=datetime.utcnow()))
    db.commit()
    db.close()

    response = client.get("/api/analysis?page=1&page_size=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    assert data["total"] == 10
```

**Step 3: 테스트 실패 확인**
```bash
docker compose exec backend pytest tests/test_api_analysis.py -v
# 예상: FAILED (엔드포인트 없음)
```

**Step 4: `backend/app/routers/api.py`에 분석 API 구현**
```python
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.analysis import AnalysisHistory
from app.schemas.analysis import AnalysisHistoryItem, AnalysisListResponse

router = APIRouter(prefix="/api", tags=["api"])

@router.get("/analysis", response_model=AnalysisListResponse)
async def list_analysis(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user)
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
        page_size=page_size
    )

@router.get("/analysis/{analysis_id}", response_model=AnalysisHistoryItem)
async def get_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """분석 상세 조회 (원본 이슈 정보, 유사 이슈 목록, AI 요약)"""
    record = db.query(AnalysisHistory).filter(AnalysisHistory.id == analysis_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="분석 이력을 찾을 수 없습니다")
    return AnalysisHistoryItem.model_validate(record)
```

**Step 5: 테스트 통과 확인**
```bash
docker compose exec backend pytest tests/test_api_analysis.py -v
# 예상: PASSED (5/5)
```

**Step 6: 커밋**
```bash
git add backend/app/routers/api.py backend/app/schemas/analysis.py backend/tests/test_api_analysis.py
git commit -m "feat: 분석 이력 목록/상세 API 구현 (GET /api/analysis, GET /api/analysis/{id})"
```

**완료 기준**: 분석 이력 목록 및 상세 조회 API가 페이지네이션과 함께 동작하고 테스트 5개 통과.

---

### Task 3: 백엔드 — 중복 감지, 통계, 재분석 API 구현

**우선순위**: Must Have | **예상 소요**: 1일 | **담당**: 백엔드 담당 2명

**목표**: `GET /api/duplicates`, `GET /api/stats`, `POST /api/analysis/rerun` 구현

**파일**:
- 수정: `backend/app/routers/api.py` (엔드포인트 추가)
- 수정: `backend/app/schemas/analysis.py` (스키마 추가)
- 생성: `backend/tests/test_api_duplicates_stats.py`

**세부 단계**:

**Step 1: 스키마 추가**
```python
# backend/app/schemas/analysis.py 에 추가
from datetime import date

class DuplicateDetectionItem(BaseModel):
    id: int
    source_issue_id: int
    target_issue_id: int
    similarity_score: float
    created_at: datetime

    class Config:
        from_attributes = True

class StatsResponse(BaseModel):
    total_analyzed: int
    total_success: int
    total_failed: int
    total_no_similar: int
    total_duplicates: int
    success_rate: float
    today_analyzed: int
    today_duplicates: int

class RerunRequest(BaseModel):
    issue_id: int
    project_id: int

class RerunResponse(BaseModel):
    status: str
    message: str
    analysis_id: Optional[int] = None
```

**Step 2: 테스트 먼저 작성 (TDD)**
```python
# backend/tests/test_api_duplicates_stats.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from app.main import app
from app.db.session import Base, get_db
from app.models.analysis import AnalysisHistory, DuplicateDetection
from app.dependencies.auth import get_current_user

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def override_get_current_user():
    return {"sub": "dashboard"}

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_get_duplicates_empty():
    """중복 감지 이력이 없을 때 빈 목록"""
    response = client.get("/api/duplicates")
    assert response.status_code == 200
    assert response.json() == []

def test_get_duplicates_with_data():
    """중복 감지 이력 반환"""
    db = TestingSessionLocal()
    db.add(DuplicateDetection(source_issue_id=1, target_issue_id=2, similarity_score=0.95, created_at=datetime.utcnow()))
    db.commit()
    db.close()

    response = client.get("/api/duplicates")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["source_issue_id"] == 1
    assert data[0]["similarity_score"] == 0.95

def test_get_stats():
    """통계 API 반환 구조 확인"""
    db = TestingSessionLocal()
    db.add(AnalysisHistory(issue_id=1, project_id=1, status="success", created_at=datetime.utcnow()))
    db.add(AnalysisHistory(issue_id=2, project_id=1, status="failed", created_at=datetime.utcnow()))
    db.add(AnalysisHistory(issue_id=3, project_id=1, status="no_similar", created_at=datetime.utcnow()))
    db.add(DuplicateDetection(source_issue_id=4, target_issue_id=5, similarity_score=0.92, created_at=datetime.utcnow()))
    db.commit()
    db.close()

    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_analyzed"] == 3
    assert data["total_success"] == 1
    assert data["total_failed"] == 1
    assert data["total_no_similar"] == 1
    assert data["total_duplicates"] == 1
    assert round(data["success_rate"], 2) == 0.33

def test_rerun_analysis():
    """수동 재분석 요청 수락"""
    response = client.post("/api/analysis/rerun", json={"issue_id": 10, "project_id": 1})
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
```

**Step 3: 테스트 실패 확인**
```bash
docker compose exec backend pytest tests/test_api_duplicates_stats.py -v
# 예상: FAILED (엔드포인트 없음)
```

**Step 4: `backend/app/routers/api.py`에 엔드포인트 추가**
```python
from datetime import datetime, date
from typing import List
from app.models.analysis import DuplicateDetection
from app.schemas.analysis import DuplicateDetectionItem, StatsResponse, RerunRequest, RerunResponse
from app.services.analysis_pipeline import run_analysis
from fastapi import BackgroundTasks

@router.get("/duplicates", response_model=List[DuplicateDetectionItem])
async def list_duplicates(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """중복 감지 이력 목록 (최신 순)"""
    items = db.query(DuplicateDetection).order_by(DuplicateDetection.created_at.desc()).limit(100).all()
    return [DuplicateDetectionItem.model_validate(item) for item in items]

@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """대시보드 통계: 카테고리별 이슈 수, 중복 감지 수, 성공/실패 통계"""
    total = db.query(AnalysisHistory).count()
    success = db.query(AnalysisHistory).filter(AnalysisHistory.status == "success").count()
    failed = db.query(AnalysisHistory).filter(AnalysisHistory.status == "failed").count()
    no_similar = db.query(AnalysisHistory).filter(AnalysisHistory.status == "no_similar").count()
    duplicates = db.query(DuplicateDetection).count()

    today = date.today()
    today_analyzed = db.query(AnalysisHistory).filter(
        AnalysisHistory.created_at >= datetime.combine(today, datetime.min.time())
    ).count()
    today_duplicates = db.query(DuplicateDetection).filter(
        DuplicateDetection.created_at >= datetime.combine(today, datetime.min.time())
    ).count()

    return StatsResponse(
        total_analyzed=total,
        total_success=success,
        total_failed=failed,
        total_no_similar=no_similar,
        total_duplicates=duplicates,
        success_rate=round(success / total, 2) if total > 0 else 0.0,
        today_analyzed=today_analyzed,
        today_duplicates=today_duplicates
    )

@router.post("/analysis/rerun", status_code=202)
async def rerun_analysis(
    req: RerunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """수동 재분석 실행 — 이슈 ID와 프로젝트 ID 지정"""
    # Redmine에서 이슈 정보 조회 후 재분석 파이프라인 실행
    from app.services.redmine_client import RedmineClient
    client = RedmineClient()
    background_tasks.add_task(
        _run_reanalysis, req.issue_id, req.project_id
    )
    return RerunResponse(status="accepted", message=f"이슈 #{req.issue_id} 재분석이 시작되었습니다")

async def _run_reanalysis(issue_id: int, project_id: int):
    """재분석용 내부 함수 — Redmine에서 이슈 정보 조회 후 파이프라인 실행"""
    from app.services.redmine_client import RedmineClient
    try:
        client = RedmineClient()
        issue = await client.get_issue(issue_id)
        await run_analysis(
            issue_id=issue_id,
            project_id=project_id,
            subject=issue.get("subject", ""),
            description=issue.get("description", ""),
            force=True  # 기존 댓글 있어도 재작성
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"[재분석 실패] 이슈 #{issue_id}: {e}")
```

**Step 5: 테스트 통과 확인**
```bash
docker compose exec backend pytest tests/test_api_duplicates_stats.py -v
# 예상: PASSED (4/4)
```

**Step 6: 커밋**
```bash
git add backend/app/routers/api.py backend/app/schemas/analysis.py backend/tests/test_api_duplicates_stats.py
git commit -m "feat: 중복 감지 목록, 통계, 수동 재분석 API 구현"
```

**완료 기준**: 중복 감지 목록, 통계 API가 올바른 데이터를 반환하고, 재분석 API가 202 응답을 반환하며 4개 테스트 통과.

---

### Task 4: 백엔드 — 설정 API 구현 (`GET /api/settings`, `PUT /api/settings`)

**우선순위**: Must Have | **예상 소요**: 0.5일 | **담당**: 백엔드 담당 1명

**목표**: 임계값, 카테고리 목록 조회/수정 API — DB에 설정 저장

**파일**:
- 생성: `backend/app/models/settings.py`
- 생성: `backend/alembic/versions/0002_add_settings.py`
- 수정: `backend/app/routers/api.py`
- 생성: `backend/app/schemas/settings.py`
- 생성: `backend/tests/test_api_settings.py`

**세부 단계**:

**Step 1: `backend/app/models/settings.py` 작성**
```python
from sqlalchemy import Column, Integer, String, Float, Text
from app.db.session import Base

class AppSettings(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, default=1)
    similarity_threshold = Column(Float, default=0.3)
    duplicate_threshold = Column(Float, default=0.9)
    max_similar_issues = Column(Integer, default=5)
    category_list = Column(Text, default="")     # 쉼표 구분 카테고리 목록
    enable_auto_comment = Column(String(10), default="false")
```

**Step 2: `backend/app/schemas/settings.py` 작성**
```python
from typing import List, Optional
from pydantic import BaseModel, Field

class SettingsResponse(BaseModel):
    similarity_threshold: float
    duplicate_threshold: float
    max_similar_issues: int
    category_list: List[str]
    enable_auto_comment: bool

class SettingsUpdateRequest(BaseModel):
    similarity_threshold: Optional[float] = Field(None, ge=0.1, le=1.0)
    duplicate_threshold: Optional[float] = Field(None, ge=0.1, le=1.0)
    max_similar_issues: Optional[int] = Field(None, ge=1, le=20)
    category_list: Optional[List[str]] = None
    enable_auto_comment: Optional[bool] = None
```

**Step 3: 테스트 먼저 작성**
```python
# backend/tests/test_api_settings.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.session import Base, get_db
from app.dependencies.auth import get_current_user

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = lambda: {"sub": "dashboard"}
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_get_settings_default():
    """설정 조회 — 기본값 반환"""
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["similarity_threshold"] == 0.3
    assert data["duplicate_threshold"] == 0.9
    assert data["max_similar_issues"] == 5

def test_update_settings():
    """설정 변경 후 조회 시 반영됨"""
    response = client.put("/api/settings", json={
        "similarity_threshold": 0.5,
        "category_list": ["버그", "기능 요청", "문의"]
    })
    assert response.status_code == 200

    get_resp = client.get("/api/settings")
    data = get_resp.json()
    assert data["similarity_threshold"] == 0.5
    assert "버그" in data["category_list"]

def test_update_settings_invalid_threshold():
    """임계값 범위 초과 시 422"""
    response = client.put("/api/settings", json={"similarity_threshold": 1.5})
    assert response.status_code == 422
```

**Step 4: `backend/app/routers/api.py`에 설정 API 추가**
```python
from app.models.settings import AppSettings
from app.schemas.settings import SettingsResponse, SettingsUpdateRequest

def _get_or_create_settings(db: Session) -> AppSettings:
    """설정 레코드가 없으면 기본값으로 생성"""
    settings_record = db.query(AppSettings).first()
    if not settings_record:
        settings_record = AppSettings()
        db.add(settings_record)
        db.commit()
        db.refresh(settings_record)
    return settings_record

@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """임계값, 카테고리 목록 조회"""
    s = _get_or_create_settings(db)
    return SettingsResponse(
        similarity_threshold=s.similarity_threshold,
        duplicate_threshold=s.duplicate_threshold,
        max_similar_issues=s.max_similar_issues,
        category_list=[c.strip() for c in s.category_list.split(",") if c.strip()],
        enable_auto_comment=s.enable_auto_comment == "true"
    )

@router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    req: SettingsUpdateRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user)
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
        s.enable_auto_comment = "true" if req.enable_auto_comment else "false"
    db.commit()
    db.refresh(s)
    return SettingsResponse(
        similarity_threshold=s.similarity_threshold,
        duplicate_threshold=s.duplicate_threshold,
        max_similar_issues=s.max_similar_issues,
        category_list=[c.strip() for c in s.category_list.split(",") if c.strip()],
        enable_auto_comment=s.enable_auto_comment == "true"
    )
```

**Step 5: Alembic 마이그레이션 추가**
```bash
docker compose exec backend alembic revision --autogenerate -m "add_app_settings"
docker compose exec backend alembic upgrade head
```

**Step 6: 테스트 통과 확인**
```bash
docker compose exec backend pytest tests/test_api_settings.py -v
# 예상: PASSED (3/3)
```

**Step 7: 커밋**
```bash
git add backend/app/models/settings.py backend/app/schemas/settings.py backend/tests/test_api_settings.py
git commit -m "feat: 설정 조회/수정 API 구현 (GET/PUT /api/settings)"
```

**완료 기준**: 설정 조회, 수정, 범위 검증 테스트 3개 통과. 설정 변경 후 즉시 조회에 반영됨.

---

### Task 5: 프론트엔드 — Vue.js 3 프로젝트 초기화 및 Docker 빌드 통합

**우선순위**: Must Have | **예상 소요**: 1일 | **담당**: 프론트엔드 담당 2명

**목표**: `frontend/` 디렉토리에 Vue.js 3 프로젝트 초기화 및 Docker 빌드 시 FastAPI `static/` 서빙 통합

**파일**:
- 생성: `frontend/` (Vite 프로젝트)
- 수정: `docker-compose.yml` (프론트엔드 빌드 스테이지 추가)
- 수정: `backend/Dockerfile` (멀티스테이지 빌드)
- 수정: `backend/app/main.py` (정적 파일 서빙 추가)

**세부 단계**:

**Step 1: Vue.js 3 프로젝트 생성**
```bash
# 로컬 개발 환경에서 실행 (Node.js 18+ 필요)
npm create vue@latest frontend -- --router --pinia --typescript
cd frontend
npm install axios markdown-it
```

**Step 2: `frontend/vite.config.ts` 수정 — API 프록시 설정**
```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: '../backend/static',  // FastAPI static 디렉토리로 빌드
    emptyOutDir: true
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',  // 개발 시 백엔드 프록시
    }
  }
})
```

**Step 3: `backend/Dockerfile` 멀티스테이지 빌드로 수정**
```dockerfile
# 스테이지 1: 프론트엔드 빌드
FROM node:20-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
# 빌드 결과: /frontend/../backend/static → /backend/static

# 스테이지 2: 백엔드
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
# 프론트엔드 빌드 결과물 복사
COPY --from=frontend-builder /backend/static ./static
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
```

> **참고**: Vite의 `outDir`을 `../backend/static`으로 설정하면 프론트엔드 빌드 결과가 직접 backend/static에 생성됩니다. 멀티스테이지 빌드에서는 COPY 경로를 실제 빌드 산출물 위치에 맞춰 조정합니다.

**Step 4: `backend/app/main.py`에 정적 파일 서빙 추가**
```python
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# ... 기존 코드 ...

# Vue.js 정적 파일 서빙 (빌드된 파일이 있을 때만)
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{path:path}", include_in_schema=False)
    async def serve_spa(path: str = ""):
        """Vue.js SPA — 모든 경로에서 index.html 반환 (Vue Router가 처리)"""
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"error": "Frontend not built"}
```

**Step 5: `docker-compose.yml` 포트 수정 (8000 → 8080)**
```yaml
version: "3.9"
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    ports:
      - "8080:8080"
    volumes:
      - ./data:/data
    env_file:
      - .env
    environment:
      - DATABASE_URL=sqlite:////data/redmine_helper.db
```

**Step 6: 로컬 빌드 테스트**
```bash
# 로컬에서 프론트엔드 빌드 확인
cd frontend && npm run build
# backend/static/index.html 생성 확인

# Docker 전체 빌드
docker compose up --build
# http://localhost:8080 접속 → Vue.js 앱이 로드되는지 확인
```

**Step 7: 커밋**
```bash
git add frontend/ backend/Dockerfile docker-compose.yml backend/app/main.py
git commit -m "feat: Vue.js 3 프로젝트 초기화 및 FastAPI 정적 파일 서빙 통합"
```

**완료 기준**: `docker compose up --build` 후 `http://localhost:8080` 접속 시 Vue.js 앱이 표시된다.

---

### Task 6: 프론트엔드 — Axios 클라이언트 및 Pinia 스토어 설정

**우선순위**: Must Have | **예상 소요**: 0.5일 | **담당**: 프론트엔드 담당 1명

**목표**: API 호출을 위한 Axios 인스턴스 설정, 인증 토큰 자동 주입, Pinia 스토어 구조 수립

**파일**:
- 생성: `frontend/src/api/client.ts`
- 생성: `frontend/src/api/analysis.ts`
- 생성: `frontend/src/api/auth.ts`
- 생성: `frontend/src/stores/auth.ts`
- 생성: `frontend/src/stores/analysis.ts`

**세부 단계**:

**Step 1: `frontend/src/api/client.ts` 작성**
```typescript
import axios from 'axios'

// Axios 인스턴스 — Bearer 토큰 자동 주입
const apiClient = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 401 응답 시 로그인 페이지로 리다이렉트
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient
```

**Step 2: `frontend/src/api/auth.ts` 작성**
```typescript
import apiClient from './client'

export const authApi = {
  login: (password: string) =>
    apiClient.post<{ access_token: string; token_type: string }>('/auth/login', { password }),
}
```

**Step 3: `frontend/src/api/analysis.ts` 작성**
```typescript
import apiClient from './client'
import type {
  AnalysisListResponse,
  AnalysisHistoryItem,
  DuplicateDetectionItem,
  StatsResponse,
  SettingsResponse,
  SettingsUpdateRequest,
} from '@/types'

export const analysisApi = {
  // 분석 이력 목록
  list: (page = 1, pageSize = 20) =>
    apiClient.get<AnalysisListResponse>('/analysis', { params: { page, page_size: pageSize } }),

  // 분석 상세
  get: (id: number) =>
    apiClient.get<AnalysisHistoryItem>(`/analysis/${id}`),

  // 수동 재분석
  rerun: (issueId: number, projectId: number) =>
    apiClient.post('/analysis/rerun', { issue_id: issueId, project_id: projectId }),

  // 중복 감지 목록
  duplicates: () =>
    apiClient.get<DuplicateDetectionItem[]>('/duplicates'),

  // 통계
  stats: () =>
    apiClient.get<StatsResponse>('/stats'),

  // 설정 조회
  getSettings: () =>
    apiClient.get<SettingsResponse>('/settings'),

  // 설정 수정
  updateSettings: (data: SettingsUpdateRequest) =>
    apiClient.put<SettingsResponse>('/settings', data),
}
```

**Step 4: `frontend/src/stores/auth.ts` 작성**
```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const isAuthenticated = computed(() => !!token.value)

  async function login(password: string): Promise<void> {
    const { data } = await authApi.login(password)
    token.value = data.access_token
    localStorage.setItem('access_token', data.access_token)
  }

  function logout(): void {
    token.value = null
    localStorage.removeItem('access_token')
  }

  return { token, isAuthenticated, login, logout }
})
```

**Step 5: `frontend/src/types/index.ts` 작성 — API 응답 타입 정의**
```typescript
export interface SimilarIssueItem {
  id: number
  subject: string
  score: number
  is_duplicate: boolean
}

export interface AnalysisHistoryItem {
  id: number
  issue_id: number
  project_id: number
  status: 'success' | 'failed' | 'no_similar'
  similar_issues: SimilarIssueItem[] | null
  ai_summary: string | null
  created_at: string
  error_message: string | null
}

export interface AnalysisListResponse {
  items: AnalysisHistoryItem[]
  total: number
  page: number
  page_size: number
}

export interface DuplicateDetectionItem {
  id: number
  source_issue_id: number
  target_issue_id: number
  similarity_score: number
  created_at: string
}

export interface StatsResponse {
  total_analyzed: number
  total_success: number
  total_failed: number
  total_no_similar: number
  total_duplicates: number
  success_rate: number
  today_analyzed: number
  today_duplicates: number
}

export interface SettingsResponse {
  similarity_threshold: number
  duplicate_threshold: number
  max_similar_issues: number
  category_list: string[]
  enable_auto_comment: boolean
}

export interface SettingsUpdateRequest {
  similarity_threshold?: number
  duplicate_threshold?: number
  max_similar_issues?: number
  category_list?: string[]
  enable_auto_comment?: boolean
}
```

**Step 6: 커밋**
```bash
git add frontend/src/api/ frontend/src/stores/ frontend/src/types/
git commit -m "feat: Axios API 클라이언트 및 Pinia 인증/분석 스토어 설정"
```

**완료 기준**: Axios 클라이언트가 Bearer 토큰을 자동 주입하고, 401 응답 시 로그인 페이지로 리다이렉트한다.

---

### Task 7: 프론트엔드 — 로그인 화면 구현 (`/login`)

**우선순위**: Should Have | **예상 소요**: 0.5일 | **담당**: 프론트엔드 담당 1명

**목표**: DASHBOARD_PASSWORD 입력 → JWT 발급 → localStorage 저장 → 대시보드로 이동

**파일**:
- 생성: `frontend/src/views/LoginView.vue`
- 수정: `frontend/src/router/index.ts` (네비게이션 가드 추가)

**세부 단계**:

**Step 1: `frontend/src/views/LoginView.vue` 작성**
```vue
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const password = ref('')
const errorMessage = ref('')
const isLoading = ref(false)

async function handleLogin() {
  if (!password.value) return
  isLoading.value = true
  errorMessage.value = ''
  try {
    await authStore.login(password.value)
    router.push('/')
  } catch {
    errorMessage.value = '비밀번호가 올바르지 않습니다.'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="login-container">
    <div class="login-card">
      <h1 class="login-title">Redmine Helper</h1>
      <p class="login-subtitle">대시보드 로그인</p>
      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="password">비밀번호</label>
          <input
            id="password"
            v-model="password"
            type="password"
            placeholder="대시보드 비밀번호 입력"
            :disabled="isLoading"
            autofocus
          />
        </div>
        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
        <button type="submit" :disabled="isLoading || !password" class="login-button">
          {{ isLoading ? '로그인 중...' : '로그인' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
}
.login-card {
  background: white;
  border-radius: 8px;
  padding: 40px;
  width: 360px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}
.login-title { font-size: 24px; font-weight: 700; margin-bottom: 4px; }
.login-subtitle { color: #666; margin-bottom: 32px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 8px; font-weight: 500; }
.form-group input {
  width: 100%; padding: 10px 14px;
  border: 1px solid #ddd; border-radius: 6px;
  font-size: 14px; box-sizing: border-box;
}
.error-message { color: #e53e3e; font-size: 14px; margin-bottom: 12px; }
.login-button {
  width: 100%; padding: 12px;
  background: #3b82f6; color: white;
  border: none; border-radius: 6px;
  font-size: 15px; font-weight: 600; cursor: pointer;
}
.login-button:disabled { background: #93c5fd; cursor: not-allowed; }
</style>
```

**Step 2: `frontend/src/router/index.ts` — 라우터 설정 및 네비게이션 가드**
```typescript
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
    { path: '/', component: () => import('@/views/DashboardView.vue') },
    { path: '/analysis/:id', component: () => import('@/views/AnalysisDetailView.vue') },
    { path: '/duplicates', component: () => import('@/views/DuplicatesView.vue') },
    { path: '/settings', component: () => import('@/views/SettingsView.vue') },
  ]
})

// 네비게이션 가드 — 미인증 시 /login으로 리다이렉트
router.beforeEach((to) => {
  const authStore = useAuthStore()
  if (!to.meta.public && !authStore.isAuthenticated) {
    return '/login'
  }
  if (to.path === '/login' && authStore.isAuthenticated) {
    return '/'
  }
})

export default router
```

**Step 3: 커밋**
```bash
git add frontend/src/views/LoginView.vue frontend/src/router/
git commit -m "feat: 로그인 화면 구현 및 Vue Router 네비게이션 가드 설정"
```

**완료 기준**: 올바른 비밀번호 입력 후 대시보드로 이동, 잘못된 비밀번호 시 에러 메시지 표시, 미인증 접근 시 로그인 페이지로 리다이렉트.

---

### Task 8: 프론트엔드 — 공통 레이아웃 및 대시보드 홈 화면 구현 (`/`)

**우선순위**: Must Have | **예상 소요**: 1.5일 | **담당**: 프론트엔드 담당 2명

**목표**: 네비게이션 레이아웃 구성, 분석 이슈 목록 테이블 및 통계 요약 카드

**파일**:
- 생성: `frontend/src/components/AppLayout.vue`
- 생성: `frontend/src/components/StatsCard.vue`
- 생성: `frontend/src/components/StatusBadge.vue`
- 생성: `frontend/src/views/DashboardView.vue`
- 수정: `frontend/src/App.vue`

**세부 단계**:

**Step 1: `frontend/src/components/AppLayout.vue` 작성 — 공통 레이아웃**
```vue
<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

function logout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-layout">
    <nav class="sidebar">
      <div class="logo">Redmine Helper</div>
      <ul class="nav-menu">
        <li><RouterLink to="/">대시보드</RouterLink></li>
        <li><RouterLink to="/duplicates">중복 감지</RouterLink></li>
        <li><RouterLink to="/settings">설정</RouterLink></li>
      </ul>
      <button @click="logout" class="logout-btn">로그아웃</button>
    </nav>
    <main class="main-content">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.app-layout { display: flex; min-height: 100vh; min-width: 1280px; }
.sidebar {
  width: 220px; background: #1e293b; color: white;
  padding: 24px 0; display: flex; flex-direction: column;
}
.logo { padding: 0 20px 24px; font-size: 18px; font-weight: 700; }
.nav-menu { list-style: none; padding: 0; margin: 0; flex: 1; }
.nav-menu li a {
  display: block; padding: 12px 20px; color: #cbd5e1;
  text-decoration: none; transition: background 0.2s;
}
.nav-menu li a:hover, .nav-menu li a.router-link-active {
  background: #334155; color: white;
}
.logout-btn {
  margin: 0 20px; padding: 10px; background: #ef4444;
  color: white; border: none; border-radius: 6px; cursor: pointer;
}
.main-content { flex: 1; padding: 32px; background: #f8fafc; overflow-y: auto; }
</style>
```

**Step 2: `frontend/src/components/StatusBadge.vue` 작성**
```vue
<script setup lang="ts">
defineProps<{ status: 'success' | 'failed' | 'no_similar' }>()
const labelMap = { success: '성공', failed: '실패', no_similar: '유사 없음' }
const colorMap = { success: '#22c55e', failed: '#ef4444', no_similar: '#f59e0b' }
</script>

<template>
  <span class="badge" :style="{ backgroundColor: colorMap[status] }">
    {{ labelMap[status] }}
  </span>
</template>

<style scoped>
.badge {
  display: inline-block; padding: 2px 10px;
  border-radius: 12px; color: white; font-size: 12px; font-weight: 600;
}
</style>
```

**Step 3: `frontend/src/views/DashboardView.vue` 작성**
```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { analysisApi } from '@/api/analysis'
import type { AnalysisHistoryItem, StatsResponse } from '@/types'

const router = useRouter()
const analyses = ref<AnalysisHistoryItem[]>([])
const stats = ref<StatsResponse | null>(null)
const total = ref(0)
const currentPage = ref(1)
const isLoading = ref(false)

async function loadData() {
  isLoading.value = true
  try {
    const [listResp, statsResp] = await Promise.all([
      analysisApi.list(currentPage.value, 20),
      analysisApi.stats(),
    ])
    analyses.value = listResp.data.items
    total.value = listResp.data.total
    stats.value = statsResp.data
  } finally {
    isLoading.value = false
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('ko-KR')
}

onMounted(loadData)
</script>

<template>
  <AppLayout>
    <h2 class="page-title">대시보드</h2>

    <!-- 통계 요약 카드 -->
    <div v-if="stats" class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">오늘 처리 건수</div>
        <div class="stat-value">{{ stats.today_analyzed }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">오늘 중복 감지</div>
        <div class="stat-value warning">{{ stats.today_duplicates }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">성공률</div>
        <div class="stat-value">{{ (stats.success_rate * 100).toFixed(1) }}%</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">전체 분석</div>
        <div class="stat-value">{{ stats.total_analyzed }}</div>
      </div>
    </div>

    <!-- 분석 이력 테이블 -->
    <div class="table-container">
      <div class="table-header">
        <h3>최근 분석 이력</h3>
        <span class="total-count">총 {{ total }}건</span>
      </div>
      <table v-if="!isLoading && analyses.length > 0" class="data-table">
        <thead>
          <tr>
            <th>이슈 번호</th>
            <th>상태</th>
            <th>유사 이슈 수</th>
            <th>처리 시각</th>
            <th>상세</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in analyses" :key="item.id">
            <td>#{{ item.issue_id }}</td>
            <td><StatusBadge :status="item.status" /></td>
            <td>{{ item.similar_issues?.length ?? 0 }}건</td>
            <td>{{ formatDate(item.created_at) }}</td>
            <td>
              <button @click="router.push(`/analysis/${item.id}`)" class="detail-btn">
                상세 보기
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else-if="!isLoading" class="empty-state">분석 이력이 없습니다.</div>
      <div v-else class="loading-state">로딩 중...</div>
    </div>
  </AppLayout>
</template>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; margin-bottom: 24px; }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }
.stat-card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.stat-label { font-size: 13px; color: #64748b; margin-bottom: 8px; }
.stat-value { font-size: 28px; font-weight: 700; color: #1e293b; }
.stat-value.warning { color: #f59e0b; }
.table-container { background: white; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.table-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px 16px; }
.table-header h3 { font-size: 16px; font-weight: 600; }
.total-count { font-size: 13px; color: #64748b; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { padding: 12px 24px; text-align: left; font-size: 13px; color: #64748b; border-bottom: 1px solid #f1f5f9; }
.data-table td { padding: 14px 24px; border-bottom: 1px solid #f8fafc; }
.detail-btn { padding: 5px 12px; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.empty-state, .loading-state { padding: 40px; text-align: center; color: #94a3b8; }
</style>
```

**Step 4: 커밋**
```bash
git add frontend/src/components/ frontend/src/views/DashboardView.vue
git commit -m "feat: 공통 레이아웃 및 대시보드 홈 화면 구현"
```

**완료 기준**: 대시보드 홈에서 통계 카드 4개와 분석 이력 테이블이 표시되고, 상세 보기 버튼이 동작한다.

---

### Task 9: 프론트엔드 — 분석 상세 화면 구현 (`/analysis/:id`)

**우선순위**: Must Have | **예상 소요**: 1일 | **담당**: 프론트엔드 담당 2명

**목표**: 원본 이슈 정보, 유사 이슈 목록 (유사도 바), AI 요약 (마크다운), 수동 재분석 버튼

**파일**:
- 생성: `frontend/src/views/AnalysisDetailView.vue`
- 생성: `frontend/src/components/SimilarityBar.vue`

**세부 단계**:

**Step 1: `frontend/src/components/SimilarityBar.vue` 작성 — 유사도 퍼센트 바**
```vue
<script setup lang="ts">
const props = defineProps<{ score: number; isDuplicate: boolean }>()
const percentage = Math.round(props.score * 100)
const color = props.isDuplicate ? '#ef4444' : props.score >= 0.6 ? '#f59e0b' : '#22c55e'
</script>

<template>
  <div class="similarity-bar">
    <div class="bar-track">
      <div class="bar-fill" :style="{ width: `${percentage}%`, backgroundColor: color }" />
    </div>
    <span class="percentage">{{ percentage }}%</span>
    <span v-if="isDuplicate" class="duplicate-badge">중복 의심</span>
  </div>
</template>

<style scoped>
.similarity-bar { display: flex; align-items: center; gap: 8px; }
.bar-track { width: 120px; height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 4px; transition: width 0.3s; }
.percentage { font-size: 13px; font-weight: 600; width: 40px; }
.duplicate-badge { font-size: 11px; background: #fef2f2; color: #ef4444; border: 1px solid #fecaca; padding: 2px 8px; border-radius: 4px; }
</style>
```

**Step 2: `frontend/src/views/AnalysisDetailView.vue` 작성**
```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MarkdownIt from 'markdown-it'
import AppLayout from '@/components/AppLayout.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import SimilarityBar from '@/components/SimilarityBar.vue'
import { analysisApi } from '@/api/analysis'
import type { AnalysisHistoryItem } from '@/types'

const route = useRoute()
const router = useRouter()
const md = new MarkdownIt()

const analysis = ref<AnalysisHistoryItem | null>(null)
const isLoading = ref(false)
const isRerunning = ref(false)
const errorMsg = ref('')

async function loadAnalysis() {
  isLoading.value = true
  try {
    const { data } = await analysisApi.get(Number(route.params.id))
    analysis.value = data
  } catch {
    errorMsg.value = '분석 이력을 불러올 수 없습니다.'
  } finally {
    isLoading.value = false
  }
}

async function rerun() {
  if (!analysis.value) return
  isRerunning.value = true
  try {
    await analysisApi.rerun(analysis.value.issue_id, analysis.value.project_id)
    alert('재분석이 시작되었습니다. 잠시 후 결과를 확인해 주세요.')
    await loadAnalysis()
  } catch {
    alert('재분석 요청 중 오류가 발생했습니다.')
  } finally {
    isRerunning.value = false
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('ko-KR')
}

onMounted(loadAnalysis)
</script>

<template>
  <AppLayout>
    <div class="detail-header">
      <button @click="router.push('/')" class="back-btn">← 목록으로</button>
      <h2 class="page-title">분석 상세</h2>
    </div>

    <div v-if="isLoading" class="loading-state">로딩 중...</div>
    <div v-else-if="errorMsg" class="error-state">{{ errorMsg }}</div>

    <template v-else-if="analysis">
      <!-- 원본 이슈 정보 -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">원본 이슈 정보</span>
          <StatusBadge :status="analysis.status" />
        </div>
        <div class="info-row">
          <span class="info-label">이슈 번호</span>
          <span>#{{ analysis.issue_id }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">프로젝트 ID</span>
          <span>{{ analysis.project_id }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">처리 시각</span>
          <span>{{ formatDate(analysis.created_at) }}</span>
        </div>
        <div v-if="analysis.error_message" class="error-message">
          오류: {{ analysis.error_message }}
        </div>
      </div>

      <!-- 유사 이슈 목록 -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">유사 이슈 목록</span>
          <span class="badge">{{ analysis.similar_issues?.length ?? 0 }}건</span>
        </div>
        <div v-if="analysis.similar_issues?.length">
          <div v-for="item in analysis.similar_issues" :key="item.id" class="similar-issue-row">
            <span class="issue-id">#{{ item.id }}</span>
            <span class="issue-subject">{{ item.subject }}</span>
            <SimilarityBar :score="item.score" :is-duplicate="item.is_duplicate" />
          </div>
        </div>
        <div v-else class="empty-state">유사 이슈가 없습니다.</div>
      </div>

      <!-- AI 요약 -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">AI 요약</span>
        </div>
        <div v-if="analysis.ai_summary" class="markdown-content" v-html="md.render(analysis.ai_summary)" />
        <div v-else class="empty-state">AI 요약이 없습니다.</div>
      </div>

      <!-- 수동 재분석 -->
      <div class="action-area">
        <button @click="rerun" :disabled="isRerunning" class="rerun-btn">
          {{ isRerunning ? '재분석 중...' : '수동 재분석 실행' }}
        </button>
      </div>
    </template>
  </AppLayout>
</template>

<style scoped>
.detail-header { display: flex; align-items: center; gap: 16px; margin-bottom: 24px; }
.back-btn { background: none; border: 1px solid #e2e8f0; padding: 8px 14px; border-radius: 6px; cursor: pointer; }
.page-title { font-size: 22px; font-weight: 700; }
.card { background: white; border-radius: 8px; padding: 24px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.card-title { font-size: 16px; font-weight: 600; }
.badge { background: #f1f5f9; padding: 2px 10px; border-radius: 12px; font-size: 13px; }
.info-row { display: flex; gap: 16px; margin-bottom: 10px; }
.info-label { width: 100px; color: #64748b; font-size: 14px; }
.similar-issue-row { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid #f1f5f9; }
.issue-id { width: 60px; font-weight: 600; color: #3b82f6; }
.issue-subject { flex: 1; font-size: 14px; }
.markdown-content { line-height: 1.7; font-size: 14px; }
.empty-state { color: #94a3b8; padding: 16px 0; }
.loading-state, .error-state { padding: 40px; text-align: center; color: #94a3b8; }
.action-area { text-align: right; margin-top: 8px; }
.rerun-btn { padding: 10px 24px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; }
.rerun-btn:disabled { background: #93c5fd; cursor: not-allowed; }
</style>
```

**Step 3: 커밋**
```bash
git add frontend/src/views/AnalysisDetailView.vue frontend/src/components/SimilarityBar.vue
git commit -m "feat: 분석 상세 화면 구현 (유사 이슈 목록, AI 요약, 수동 재분석)"
```

**완료 기준**: 분석 상세 화면에서 원본 이슈 정보, 유사 이슈 유사도 바, AI 요약(마크다운 렌더링), 수동 재분석 버튼이 동작한다.

---

### Task 10: 프론트엔드 — 중복 감지 목록 화면 구현 (`/duplicates`)

**우선순위**: Must Have | **예상 소요**: 0.5일 | **담당**: 프론트엔드 담당 1명

**목표**: 중복 의심 이슈 쌍 목록, 유사도 점수, Redmine 링크 제공

**파일**:
- 생성: `frontend/src/views/DuplicatesView.vue`

**세부 단계**:

**Step 1: `frontend/src/views/DuplicatesView.vue` 작성**
```vue
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import SimilarityBar from '@/components/SimilarityBar.vue'
import { analysisApi } from '@/api/analysis'
import { analysisApi as settingsApiAlias } from '@/api/analysis'
import type { DuplicateDetectionItem } from '@/types'

// Redmine URL은 설정에서 가져오거나 환경 변수에서 주입
const redmineUrl = ref('')
const duplicates = ref<DuplicateDetectionItem[]>([])
const isLoading = ref(false)

async function loadData() {
  isLoading.value = true
  try {
    const [dupResp, settingsResp] = await Promise.all([
      analysisApi.duplicates(),
      analysisApi.getSettings(),
    ])
    duplicates.value = dupResp.data
    // 설정에서 Redmine URL을 별도로 관리하거나, 환경변수로 주입 가능
    // 여기서는 별도 API 필드가 없으므로 빈 문자열로 처리
  } finally {
    isLoading.value = false
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('ko-KR')
}

function redmineIssueUrl(issueId: number): string {
  if (!redmineUrl.value) return '#'
  return `${redmineUrl.value}/issues/${issueId}`
}

onMounted(loadData)
</script>

<template>
  <AppLayout>
    <h2 class="page-title">중복 감지 이력</h2>

    <div class="table-container">
      <div class="table-header">
        <span class="total-count">총 {{ duplicates.length }}건</span>
      </div>
      <table v-if="!isLoading && duplicates.length > 0" class="data-table">
        <thead>
          <tr>
            <th>원본 이슈</th>
            <th>중복 의심 이슈</th>
            <th>유사도</th>
            <th>감지 일시</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in duplicates" :key="item.id">
            <td>
              <a :href="redmineIssueUrl(item.source_issue_id)" target="_blank" class="issue-link">
                #{{ item.source_issue_id }}
              </a>
            </td>
            <td>
              <a :href="redmineIssueUrl(item.target_issue_id)" target="_blank" class="issue-link">
                #{{ item.target_issue_id }}
              </a>
            </td>
            <td>
              <SimilarityBar :score="item.similarity_score" :is-duplicate="true" />
            </td>
            <td>{{ formatDate(item.created_at) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else-if="!isLoading" class="empty-state">중복 감지 이력이 없습니다.</div>
      <div v-else class="loading-state">로딩 중...</div>
    </div>
  </AppLayout>
</template>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; margin-bottom: 24px; }
.table-container { background: white; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.table-header { padding: 20px 24px 16px; }
.total-count { font-size: 13px; color: #64748b; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { padding: 12px 24px; text-align: left; font-size: 13px; color: #64748b; border-bottom: 1px solid #f1f5f9; }
.data-table td { padding: 14px 24px; border-bottom: 1px solid #f8fafc; }
.issue-link { color: #3b82f6; font-weight: 600; text-decoration: none; }
.issue-link:hover { text-decoration: underline; }
.empty-state, .loading-state { padding: 40px; text-align: center; color: #94a3b8; }
</style>
```

**Step 2: 커밋**
```bash
git add frontend/src/views/DuplicatesView.vue
git commit -m "feat: 중복 감지 목록 화면 구현 (유사도 바, Redmine 링크)"
```

**완료 기준**: 중복 감지 목록에서 원본/중복 이슈 쌍, 유사도 바, 감지 일시가 표시된다.

---

### Task 11: 프론트엔드 — 설정 화면 구현 (`/settings`)

**우선순위**: Must Have | **예상 소요**: 1일 | **담당**: 프론트엔드 담당 2명

**목표**: 유사도/중복 감지 임계값 슬라이더, 카테고리 목록 편집, 저장 기능

**파일**:
- 생성: `frontend/src/views/SettingsView.vue`

**세부 단계**:

**Step 1: `frontend/src/views/SettingsView.vue` 작성**
```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import { analysisApi } from '@/api/analysis'

const similarityThreshold = ref(0.3)
const duplicateThreshold = ref(0.9)
const maxSimilarIssues = ref(5)
const categoryList = ref<string[]>([])
const newCategory = ref('')
const isSaving = ref(false)
const saveMessage = ref('')

async function loadSettings() {
  const { data } = await analysisApi.getSettings()
  similarityThreshold.value = data.similarity_threshold
  duplicateThreshold.value = data.duplicate_threshold
  maxSimilarIssues.value = data.max_similar_issues
  categoryList.value = [...data.category_list]
}

function addCategory() {
  const cat = newCategory.value.trim()
  if (cat && !categoryList.value.includes(cat)) {
    categoryList.value.push(cat)
    newCategory.value = ''
  }
}

function removeCategory(index: number) {
  categoryList.value.splice(index, 1)
}

async function saveSettings() {
  isSaving.value = true
  saveMessage.value = ''
  try {
    await analysisApi.updateSettings({
      similarity_threshold: similarityThreshold.value,
      duplicate_threshold: duplicateThreshold.value,
      max_similar_issues: maxSimilarIssues.value,
      category_list: categoryList.value,
    })
    saveMessage.value = '설정이 저장되었습니다.'
    setTimeout(() => { saveMessage.value = '' }, 3000)
  } catch {
    saveMessage.value = '저장 중 오류가 발생했습니다.'
  } finally {
    isSaving.value = false
  }
}

onMounted(loadSettings)
</script>

<template>
  <AppLayout>
    <h2 class="page-title">설정</h2>

    <div class="settings-card">
      <h3 class="section-title">유사도 임계값</h3>

      <div class="setting-row">
        <div class="setting-info">
          <label>유사 이슈 탐지 임계값</label>
          <p class="setting-desc">이 값 이상인 이슈만 유사 이슈로 표시합니다.</p>
        </div>
        <div class="slider-group">
          <input
            v-model.number="similarityThreshold"
            type="range" min="0.1" max="1.0" step="0.05"
            class="slider"
          />
          <span class="slider-value">{{ (similarityThreshold * 100).toFixed(0) }}%</span>
        </div>
      </div>

      <div class="setting-row">
        <div class="setting-info">
          <label>중복 감지 임계값</label>
          <p class="setting-desc">이 값 이상이면 중복 이슈로 플래그 처리됩니다.</p>
        </div>
        <div class="slider-group">
          <input
            v-model.number="duplicateThreshold"
            type="range" min="0.1" max="1.0" step="0.05"
            class="slider"
          />
          <span class="slider-value">{{ (duplicateThreshold * 100).toFixed(0) }}%</span>
        </div>
      </div>

      <div class="setting-row">
        <div class="setting-info">
          <label>최대 유사 이슈 수</label>
          <p class="setting-desc">분석 결과에 표시할 최대 유사 이슈 건수입니다.</p>
        </div>
        <div class="slider-group">
          <input
            v-model.number="maxSimilarIssues"
            type="range" min="1" max="20" step="1"
            class="slider"
          />
          <span class="slider-value">{{ maxSimilarIssues }}건</span>
        </div>
      </div>
    </div>

    <div class="settings-card">
      <h3 class="section-title">카테고리 목록</h3>
      <div class="category-list">
        <div v-for="(cat, index) in categoryList" :key="cat" class="category-tag">
          {{ cat }}
          <button @click="removeCategory(index)" class="remove-btn">×</button>
        </div>
      </div>
      <div class="add-category">
        <input
          v-model="newCategory"
          placeholder="새 카테고리 입력"
          @keyup.enter="addCategory"
          class="category-input"
        />
        <button @click="addCategory" class="add-btn">추가</button>
      </div>
    </div>

    <div class="action-area">
      <span v-if="saveMessage" class="save-message">{{ saveMessage }}</span>
      <button @click="saveSettings" :disabled="isSaving" class="save-btn">
        {{ isSaving ? '저장 중...' : '설정 저장' }}
      </button>
    </div>
  </AppLayout>
</template>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; margin-bottom: 24px; }
.settings-card { background: white; border-radius: 8px; padding: 28px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.section-title { font-size: 16px; font-weight: 600; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 1px solid #f1f5f9; }
.setting-row { display: flex; justify-content: space-between; align-items: flex-start; padding: 14px 0; border-bottom: 1px solid #f8fafc; }
.setting-info label { font-weight: 500; display: block; margin-bottom: 4px; }
.setting-desc { font-size: 13px; color: #64748b; margin: 0; }
.slider-group { display: flex; align-items: center; gap: 12px; }
.slider { width: 200px; }
.slider-value { width: 50px; text-align: right; font-weight: 600; }
.category-list { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; min-height: 36px; }
.category-tag { display: flex; align-items: center; gap: 6px; background: #eff6ff; color: #3b82f6; border: 1px solid #bfdbfe; border-radius: 16px; padding: 4px 12px; font-size: 13px; }
.remove-btn { background: none; border: none; cursor: pointer; color: #93c5fd; font-size: 16px; line-height: 1; padding: 0; }
.remove-btn:hover { color: #ef4444; }
.add-category { display: flex; gap: 8px; }
.category-input { flex: 1; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 14px; }
.add-btn { padding: 8px 16px; background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 6px; cursor: pointer; font-size: 14px; }
.action-area { display: flex; justify-content: flex-end; align-items: center; gap: 16px; }
.save-message { font-size: 14px; color: #22c55e; }
.save-btn { padding: 12px 28px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 15px; font-weight: 600; }
.save-btn:disabled { background: #93c5fd; cursor: not-allowed; }
</style>
```

**Step 2: 커밋**
```bash
git add frontend/src/views/SettingsView.vue
git commit -m "feat: 설정 화면 구현 (임계값 슬라이더, 카테고리 목록 편집)"
```

**완료 기준**: 임계값 슬라이더 조작 후 저장하면 API에 반영되고 이후 분석에 적용된다. 카테고리 추가/삭제가 동작한다.

---

### Task 12: E2E 통합 검증

**우선순위**: Must Have | **예상 소요**: 0.5일 | **담당**: QA + 전체 팀

**목표**: `docker compose up --build` 후 전체 대시보드 기능 동작 확인

**세부 단계**:

**Step 1: Docker 전체 빌드 및 마이그레이션**
```bash
docker compose up --build -d
docker compose exec backend alembic upgrade head
```

**Step 2: 백엔드 API 테스트 전체 실행**
```bash
docker compose exec backend pytest -v --cov=app --cov-report=term-missing
# 목표: 전체 테스트 통과
```

**Step 3: 대시보드 접근 확인**
```bash
# 로그인 API 테스트
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password": "your_dashboard_password"}'
# 예상: {"access_token": "...", "token_type": "bearer"}
```

**Step 4: 분석 이력 API 확인 (토큰 발급 후)**
```bash
TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password": "your_dashboard_password"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl http://localhost:8080/api/analysis -H "Authorization: Bearer $TOKEN"
curl http://localhost:8080/api/stats -H "Authorization: Bearer $TOKEN"
curl http://localhost:8080/api/settings -H "Authorization: Bearer $TOKEN"
```

**Step 5: Vue.js 대시보드 브라우저 확인 (수동)**
```
http://localhost:8080         → 로그인 화면 표시 확인
http://localhost:8080/login   → 비밀번호 입력 → 로그인 성공 → 대시보드 이동
http://localhost:8080/        → 통계 카드 + 분석 이력 테이블 표시
http://localhost:8080/analysis/1 → 분석 상세 화면 표시
http://localhost:8080/duplicates → 중복 감지 목록 표시
http://localhost:8080/settings   → 설정 화면 표시
```

**Step 6: 최종 커밋**
```bash
git add .
git commit -m "chore: Sprint 3 E2E 통합 검증 완료"
```

**완료 기준**: Sprint 3 Definition of Done 전체 항목 충족.

---

## 의존성 및 리스크

### 태스크 간 의존성

```
Task 1 (JWT 인증 미들웨어)
    ├── Task 2 (분석 이력 API)
    ├── Task 3 (중복/통계/재분석 API)
    └── Task 4 (설정 API)
            └── Task 5 (Vue.js 프로젝트 초기화 + Docker 통합)
                    └── Task 6 (Axios 클라이언트 + Pinia 스토어)
                            ├── Task 7 (로그인 화면)
                            ├── Task 8 (대시보드 홈)  ← Task 2, 3 완료 필요
                            ├── Task 9 (분석 상세)   ← Task 2 완료 필요
                            ├── Task 10 (중복 감지 목록) ← Task 3 완료 필요
                            └── Task 11 (설정 화면) ← Task 4 완료 필요
                                    └── Task 12 (E2E 검증) ← 전체 완료 필요
```

### 리스크 및 대응 방안

| 리스크 | 가능성 | 영향도 | 대응 방안 |
|--------|--------|--------|-----------|
| Docker 멀티스테이지 빌드 경로 오류 | 중간 | 중간 | Vite `outDir` 경로와 Dockerfile `COPY` 경로 일치 여부 사전 검증 |
| Vue Router SPA 새로고침 404 | 낮음 | 중간 | FastAPI의 catch-all 라우트(`/{path:path}`)가 API 경로와 충돌하지 않도록 순서 관리 |
| JWT 토큰 만료 UX | 낮음 | 낮음 | Axios 인터셉터에서 401 시 자동 로그인 페이지 이동으로 처리 |
| 설정 API와 `app.config.settings` 동기화 | 중간 | 중간 | DB 설정을 캐시로 읽어오는 미들웨어 추가 또는 분석 파이프라인에서 매번 DB 조회 |
| 마크다운 XSS 취약점 | 낮음 | 낮음 | `markdown-it` 기본 이스케이프 적용, AI 요약은 서버에서 생성된 신뢰 데이터이므로 허용 범위 내 |

### 사전 준비 사항 (착수 전 확인 필요)

- ⬜ Node.js 18+ 개발 환경 세팅 (Vue.js 프로젝트 초기화용)
- ⬜ Sprint 2에서 구현된 `run_analysis` 함수가 `force` 파라미터를 지원하는지 확인
- ⬜ `DASHBOARD_PASSWORD` `.env`에 설정 여부 확인
- ⬜ Docker Compose 포트 변경 (8000 → 8080) 팀 공유

---

## 팀 역할 분담 (10명 기준)

| 역할 | 인원 | 담당 태스크 |
|------|------|-------------|
| 백엔드 리드 | 1명 | Task 1 (인증), Task 4 (설정 API) |
| 백엔드 개발 | 3명 | Task 2 (분석 이력 API), Task 3 (중복/통계/재분석 API) |
| 프론트엔드 리드 | 1명 | Task 5 (Vue.js 초기화), Task 6 (Axios/Pinia) |
| 프론트엔드 개발 | 3명 | Task 7~8 (로그인/홈), Task 9~10 (상세/중복), Task 11 (설정) |
| QA | 1명 | Task 12 (E2E 검증), 전체 테스트 리뷰 |
| PM/아키텍트 | 1명 | 코드 리뷰, 스프린트 진행 관리, Sprint 4 준비 |

---

## 완료 기준 (Definition of Done)

| # | 항목 | 확인 방법 |
|---|------|-----------|
| 1 | ⬜ `docker compose up --build` 후 `http://localhost:8080` 접속 시 로그인 화면 표시 | 브라우저 접속 |
| 2 | ⬜ 올바른 비밀번호 입력 후 대시보드 홈으로 이동 | 브라우저 로그인 |
| 3 | ⬜ 대시보드 홈에서 최근 100건의 분석 이력 확인 가능 | 브라우저 확인 |
| 4 | ⬜ 분석 상세 화면에서 원본 이슈 링크, 유사 이슈 목록, AI 요약 표시 | 브라우저 확인 |
| 5 | ⬜ 수동 재분석 버튼 클릭 시 재분석 실행 및 결과 갱신 | 브라우저 확인 |
| 6 | ⬜ 설정 화면에서 임계값 변경 후 저장 시 이후 분석에 적용 | API + 브라우저 확인 |
| 7 | ⬜ 백엔드 API 전체 단위 테스트 통과 | `pytest -v` 결과 |
| 8 | ⬜ 토큰 없는 API 접근 → HTTP 401 반환 | `curl` 테스트 |

---

## 예상 산출물

| 산출물 | 경로 | 설명 |
|--------|------|------|
| 인증 라우터 | `backend/app/routers/auth.py` | JWT 로그인 API |
| 인증 의존성 | `backend/app/dependencies/auth.py` | Bearer 토큰 검증 |
| 대시보드 API | `backend/app/routers/api.py` | 분석/중복/통계/설정 REST API |
| 설정 모델 | `backend/app/models/settings.py` | app_settings 테이블 |
| Vue.js 프로젝트 | `frontend/` | Vite + Vue Router + Pinia + Axios |
| 로그인 화면 | `frontend/src/views/LoginView.vue` | JWT 기반 로그인 |
| 대시보드 홈 | `frontend/src/views/DashboardView.vue` | 분석 이력 + 통계 |
| 분석 상세 | `frontend/src/views/AnalysisDetailView.vue` | 유사 이슈 + AI 요약 + 재분석 |
| 중복 감지 목록 | `frontend/src/views/DuplicatesView.vue` | 중복 이슈 쌍 목록 |
| 설정 화면 | `frontend/src/views/SettingsView.vue` | 임계값/카테고리 설정 |
| 백엔드 테스트 | `backend/tests/test_auth.py`, `test_api_*.py` | 단위 테스트 |
| DB 마이그레이션 | `backend/alembic/versions/0002_add_settings.py` | app_settings 테이블 추가 |

---

## 검증 결과

- [코드 리뷰 보고서](sprint3/code-review.md)
- [배포 가이드 및 검증 체크리스트](sprint3/deploy.md)

---

## 다음 스프린트 준비 사항

Sprint 3 완료 후 Sprint 4 착수 전 확인해야 할 사항:

- ⬜ 운영 환경에서 JWT_SECRET_KEY를 강력한 랜덤 값으로 교체
- ⬜ 동시 웹훅 수신 시 DB 트랜잭션 락 검토 (WAL 모드 활성화)
- ⬜ 분석 이력 90일 자동 삭제 정책 결정
- ⬜ Docker 이미지 크기 최적화 방안 검토 (멀티스테이지 빌드 개선)
- ⬜ 재시도 큐 도입 여부 결정 (Redmine 댓글 작성 실패 대응)
