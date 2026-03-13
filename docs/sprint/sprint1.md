# Sprint 1 계획서 — Redmine Helper

> **For Claude:** REQUIRED SUB-SKILL: Use writing-plans skill to implement each task in this sprint.

**스프린트 번호**: Sprint 1
**기간**: 2026-03-13 (금) ~ 2026-03-26 (목) — 2주
**팀 규모**: 개발자 10명
**작성일**: 2026-03-13

---

## 스프린트 목표

> Redmine 새 이슈 등록 시 웹훅을 수신하여 유사 이슈 목록을 검색하고 서버 로그에 출력할 수 있다.

**측정 가능한 성공 지표**:
- `docker compose up` 후 Redmine 웹훅 테스트 요청을 보내면 유사 이슈 목록이 서버 로그에 출력된다.
- 시크릿 토큰이 틀린 요청은 401을 반환한다.
- SQLite `analysis_history` 레코드가 생성된다.
- 유사도 계산 함수, 웹훅 파싱 함수 단위 테스트 커버리지 80% 이상.

---

## 구현 범위

### 포함 항목 (In Scope)

| 분류 | 항목 |
|------|------|
| 인프라 | Docker Compose 환경 구성 (`docker-compose.yml`, `Dockerfile`, `.env.example`) |
| 백엔드 구조 | FastAPI 프로젝트 디렉토리 구조 초기화 |
| DB | SQLite 스키마 설계 + Alembic 초기 마이그레이션 |
| 웹훅 | `POST /webhook/redmine` 엔드포인트 (HMAC 검증, 202 응답, BackgroundTasks) |
| 폴링 폴백 | APScheduler 1분 주기 폴링 (환경 변수로 전환 가능) |
| Redmine 클라이언트 | 이슈 목록/상세 조회, 댓글 작성 API 클라이언트 |
| 유사도 검색 | TF-IDF 기반 코사인 유사도 계산, 상위 5개 추출 |
| 연동 | 웹훅 수신 → 유사도 계산 → 로그 출력 파이프라인 |
| 테스트 | 유사도 계산, 웹훅 파싱 단위 테스트 |

### 제외 항목 (Out of Scope)

| 항목 | 이유 |
|------|------|
| Claude API 요약 생성 | Sprint 2 범위 |
| Redmine 댓글 자동 작성 | Sprint 2 범위 |
| 이슈 자동 분류/태깅 | Sprint 2 범위 |
| Vue.js 대시보드 | Sprint 3 범위 |
| 임베딩 기반 유사도 | Sprint 2 PoC 후 결정 |

---

## 기술 스택 및 아키텍처

```
[Redmine] --webhook--> [FastAPI :8000]
                            |
                    BackgroundTasks
                            |
               ┌────────────┴─────────────┐
               │                          │
    [Redmine API Client]     [Similarity Service]
    (httpx AsyncClient)       (scikit-learn TF-IDF)
               │                          │
               └────────────┬─────────────┘
                            │
                     [SQLite DB]
                   (analysis_history)
```

**주요 기술**:
- Python 3.11+, FastAPI, Uvicorn
- httpx (AsyncClient, Redmine API 호출)
- scikit-learn (TF-IDF, 코사인 유사도)
- SQLAlchemy + Alembic (ORM, 마이그레이션)
- APScheduler (폴링 폴백)
- pytest + httpx TestClient (테스트)
- Docker + Docker Compose

---

## 작업 분해 (Task Breakdown)

### Task 1: Docker Compose 환경 구성

**우선순위**: Must Have | **예상 소요**: 0.5일 | **담당**: 인프라 담당 1명

**목표**: `docker compose up` 으로 FastAPI 서버가 기동되는 최소 환경 구성

**파일**:
- 생성: `docker-compose.yml`
- 생성: `backend/Dockerfile`
- 생성: `.env.example`
- 생성: `backend/requirements.txt`

**세부 단계**:

**Step 1: `.env.example` 파일 작성**
```bash
# .env.example
REDMINE_URL=http://your-redmine.example.com
REDMINE_API_KEY=your_redmine_api_key
CLAUDE_API_KEY=your_claude_api_key
WEBHOOK_SECRET=your_webhook_secret_token
DASHBOARD_PASSWORD=your_dashboard_password
ISSUE_DETECTION_MODE=webhook   # webhook | polling
SIMILARITY_THRESHOLD=0.3
DUPLICATE_THRESHOLD=0.9
MAX_SIMILAR_ISSUES=5
ISSUE_SEARCH_DAYS=365
```

**Step 2: `backend/requirements.txt` 작성**
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
httpx==0.27.0
sqlalchemy==2.0.35
alembic==1.13.3
scikit-learn==1.5.2
apscheduler==3.10.4
python-dotenv==1.0.1
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-cov==5.0.0
```

**Step 3: `backend/Dockerfile` 작성**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**Step 4: `docker-compose.yml` 작성**
```yaml
version: "3.9"
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./data:/data
    env_file:
      - .env
    environment:
      - DATABASE_URL=sqlite:////data/redmine_helper.db
```

**Step 5: 동작 확인**
```bash
cp .env.example .env
docker compose up --build
# http://localhost:8000/docs 접속 확인
```

**완료 기준**: `docker compose up` 후 `http://localhost:8000/docs` 접속 시 FastAPI Swagger UI가 표시된다.

---

### Task 2: FastAPI 프로젝트 구조 초기화

**우선순위**: Must Have | **예상 소요**: 0.5일 | **담당**: 백엔드 담당 1명

**목표**: 라우터, 서비스, 모델, DB 의존성 주입 기반의 프로젝트 구조 수립

**파일**:
- 생성: `backend/app/__init__.py`
- 생성: `backend/app/main.py`
- 생성: `backend/app/config.py`
- 생성: `backend/app/routers/__init__.py`
- 생성: `backend/app/services/__init__.py`
- 생성: `backend/app/models/__init__.py`
- 생성: `backend/app/db/__init__.py`
- 생성: `backend/app/db/session.py`

**세부 단계**:

**Step 1: `backend/app/config.py` 작성**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    redmine_url: str
    redmine_api_key: str
    claude_api_key: str
    webhook_secret: str
    dashboard_password: str
    issue_detection_mode: str = "webhook"
    similarity_threshold: float = 0.3
    duplicate_threshold: float = 0.9
    max_similar_issues: int = 5
    issue_search_days: int = 365
    database_url: str = "sqlite:////data/redmine_helper.db"

    class Config:
        env_file = ".env"

settings = Settings()
```

**Step 2: `backend/app/db/session.py` 작성**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Step 3: `backend/app/main.py` 작성**
```python
from fastapi import FastAPI
from app.routers import webhook

app = FastAPI(title="Redmine Helper", version="1.0.0")
app.include_router(webhook.router)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

**Step 4: 테스트 작성 및 실행**
```bash
# backend/tests/test_main.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```
```bash
docker compose exec backend pytest tests/test_main.py -v
```

**Step 5: 커밋**
```bash
git add backend/
git commit -m "feat: FastAPI 프로젝트 기본 구조 초기화"
```

**완료 기준**: `/health` 엔드포인트가 200 응답을 반환한다.

---

### Task 3: SQLite 스키마 설계 및 Alembic 초기 마이그레이션

**우선순위**: Must Have | **예상 소요**: 0.5일 | **담당**: 백엔드 담당 1명

**목표**: `analysis_history`, `duplicate_detections` 테이블 생성

**파일**:
- 생성: `backend/app/models/analysis.py`
- 생성: `backend/alembic.ini`
- 생성: `backend/alembic/env.py` (alembic init 후 수정)
- 생성: `backend/alembic/versions/0001_initial.py`

**세부 단계**:

**Step 1: `backend/app/models/analysis.py` 작성**
```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from app.db.session import Base

class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, nullable=False, index=True)
    project_id = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False)  # success | failed | no_similar
    similar_issues = Column(JSON, nullable=True)  # [{id, title, score}]
    ai_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    error_message = Column(Text, nullable=True)

class DuplicateDetection(Base):
    __tablename__ = "duplicate_detections"

    id = Column(Integer, primary_key=True, index=True)
    source_issue_id = Column(Integer, nullable=False, index=True)
    target_issue_id = Column(Integer, nullable=False)
    similarity_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Step 2: Alembic 초기화 및 마이그레이션 생성**
```bash
docker compose exec backend alembic init alembic
# alembic/env.py에서 target_metadata 설정
docker compose exec backend alembic revision --autogenerate -m "initial"
docker compose exec backend alembic upgrade head
```

**Step 3: 마이그레이션 동작 확인**
```bash
docker compose exec backend python -c "
from app.db.session import engine
from sqlalchemy import inspect
inspector = inspect(engine)
print(inspector.get_table_names())
# 출력: ['analysis_history', 'duplicate_detections', 'alembic_version']
"
```

**Step 4: 커밋**
```bash
git add backend/app/models/ backend/alembic/
git commit -m "feat: SQLite 스키마 및 Alembic 마이그레이션 초기화"
```

**완료 기준**: `alembic upgrade head` 실행 후 두 테이블이 생성된다.

---

### Task 4: Redmine 웹훅 수신 엔드포인트 구현

**우선순위**: Must Have | **예상 소요**: 1일 | **담당**: 백엔드 담당 2명

**목표**: `POST /webhook/redmine` — HMAC 검증 → 이벤트 파싱 → 202 즉시 응답 → BackgroundTasks 처리

**파일**:
- 생성: `backend/app/routers/webhook.py`
- 생성: `backend/app/schemas/webhook.py`
- 생성: `backend/tests/test_webhook.py`

**세부 단계**:

**Step 1: `backend/app/schemas/webhook.py` 작성 (Pydantic 모델)**
```python
from pydantic import BaseModel
from typing import Optional

class RedmineIssue(BaseModel):
    id: int
    subject: str
    description: Optional[str] = ""
    project: dict  # {"id": 1, "name": "..."}

class RedmineWebhookPayload(BaseModel):
    action: str  # "opened", "created" 등
    issue: RedmineIssue
```

**Step 2: 테스트 먼저 작성 (TDD)**
```python
# backend/tests/test_webhook.py
import hashlib, hmac, json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
SECRET = "test_secret"

def make_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

def test_webhook_valid_request():
    payload = {"action": "opened", "issue": {"id": 1, "subject": "테스트 이슈", "description": "내용", "project": {"id": 1, "name": "프로젝트"}}}
    body = json.dumps(payload).encode()
    sig = make_signature(body, SECRET)
    response = client.post("/webhook/redmine", content=body, headers={"X-Redmine-Token": sig, "Content-Type": "application/json"})
    assert response.status_code == 202

def test_webhook_invalid_token():
    payload = {"action": "opened", "issue": {"id": 1, "subject": "테스트", "description": "", "project": {"id": 1, "name": "프로젝트"}}}
    body = json.dumps(payload).encode()
    response = client.post("/webhook/redmine", content=body, headers={"X-Redmine-Token": "wrong_token", "Content-Type": "application/json"})
    assert response.status_code == 401

def test_webhook_non_issue_created_event():
    payload = {"action": "updated", "issue": {"id": 1, "subject": "테스트", "description": "", "project": {"id": 1, "name": "프로젝트"}}}
    body = json.dumps(payload).encode()
    sig = make_signature(body, SECRET)
    response = client.post("/webhook/redmine", content=body, headers={"X-Redmine-Token": sig, "Content-Type": "application/json"})
    assert response.status_code == 200  # 무시하되 에러는 아님
```

**Step 3: 테스트 실패 확인**
```bash
docker compose exec backend pytest tests/test_webhook.py -v
# 예상: FAILED (엔드포인트 없음)
```

**Step 4: `backend/app/routers/webhook.py` 구현**
```python
import hashlib, hmac
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from app.config import settings
from app.schemas.webhook import RedmineWebhookPayload

router = APIRouter(prefix="/webhook", tags=["webhook"])

def verify_signature(body: bytes, token: str) -> bool:
    expected = hmac.new(settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, token)

async def process_webhook(issue_id: int, project_id: int, subject: str, description: str):
    # Task 5, 6에서 구현 예정 — 현재는 로그만 출력
    import logging
    logging.info(f"[웹훅 수신] 이슈 #{issue_id}: {subject} (프로젝트 {project_id})")

@router.post("/redmine")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    token = request.headers.get("X-Redmine-Token", "")
    if not verify_signature(body, token):
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    try:
        payload = RedmineWebhookPayload.model_validate_json(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")

    # issue_created 이벤트만 처리
    if payload.action not in ("opened", "created"):
        return {"status": "ignored"}

    background_tasks.add_task(
        process_webhook,
        payload.issue.id,
        payload.issue.project["id"],
        payload.issue.subject,
        payload.issue.description or ""
    )
    return {"status": "accepted"}, 202  # HTTP 202
```

**Step 5: 테스트 통과 확인**
```bash
docker compose exec backend pytest tests/test_webhook.py -v
# 예상: PASSED (3/3)
```

**Step 6: 커밋**
```bash
git add backend/app/routers/webhook.py backend/app/schemas/ backend/tests/test_webhook.py
git commit -m "feat: Redmine 웹훅 수신 엔드포인트 구현 (HMAC 검증, 202 응답)"
```

**완료 기준**: 유효한 웹훅 → 202, 잘못된 토큰 → 401, 잘못된 페이로드 → 400.

---

### Task 5: Redmine REST API 클라이언트 구현

**우선순위**: Must Have | **예상 소요**: 1일 | **담당**: 백엔드 담당 2명

**목표**: 이슈 목록/상세 조회, 댓글 작성이 가능한 비동기 httpx 클라이언트

**파일**:
- 생성: `backend/app/services/redmine_client.py`
- 생성: `backend/tests/test_redmine_client.py`

**세부 단계**:

**Step 1: 테스트 먼저 작성 (respx로 Redmine API 모킹)**

`requirements.txt`에 `respx==0.21.1` 추가 후:

```python
# backend/tests/test_redmine_client.py
import pytest, respx, httpx
from app.services.redmine_client import RedmineClient

@pytest.mark.asyncio
@respx.mock
async def test_get_issues():
    respx.get("http://redmine.test/issues.json").mock(
        return_value=httpx.Response(200, json={"issues": [{"id": 1, "subject": "테스트", "description": "내용", "project": {"id": 1}}]})
    )
    client = RedmineClient(base_url="http://redmine.test", api_key="testkey")
    issues = await client.get_issues(project_id=1)
    assert len(issues) == 1
    assert issues[0]["id"] == 1

@pytest.mark.asyncio
@respx.mock
async def test_post_comment():
    respx.put("http://redmine.test/issues/1.json").mock(
        return_value=httpx.Response(200, json={})
    )
    client = RedmineClient(base_url="http://redmine.test", api_key="testkey")
    await client.post_comment(issue_id=1, comment="테스트 댓글")
    assert respx.calls.called
```

**Step 2: 테스트 실패 확인**
```bash
docker compose exec backend pytest tests/test_redmine_client.py -v
# 예상: FAILED (모듈 없음)
```

**Step 3: `backend/app/services/redmine_client.py` 구현**
```python
from datetime import datetime, timedelta
import httpx
from app.config import settings

class RedmineClient:
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = (base_url or settings.redmine_url).rstrip("/")
        self.api_key = api_key or settings.redmine_api_key
        self.headers = {"X-Redmine-API-Key": self.api_key, "Content-Type": "application/json"}

    async def get_issues(self, project_id: int) -> list[dict]:
        """지정 프로젝트의 최근 N일 이슈 목록 조회"""
        since = (datetime.utcnow() - timedelta(days=settings.issue_search_days)).strftime("%Y-%m-%d")
        params = {"project_id": project_id, "created_on": f">={since}", "limit": 100, "status_id": "*"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            for attempt in range(2):
                try:
                    r = await client.get(f"{self.base_url}/issues.json", params=params, headers=self.headers)
                    r.raise_for_status()
                    return r.json().get("issues", [])
                except (httpx.HTTPError, httpx.TimeoutException):
                    if attempt == 1:
                        raise
        return []

    async def get_issue(self, issue_id: int) -> dict:
        """이슈 상세 (댓글 포함) 조회"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{self.base_url}/issues/{issue_id}.json", params={"include": "journals"}, headers=self.headers)
            r.raise_for_status()
            return r.json().get("issue", {})

    async def post_comment(self, issue_id: int, comment: str) -> None:
        """이슈에 댓글 작성"""
        body = {"issue": {"notes": comment}}
        async with httpx.AsyncClient(timeout=10.0) as client:
            for attempt in range(2):
                try:
                    r = await client.put(f"{self.base_url}/issues/{issue_id}.json", json=body, headers=self.headers)
                    r.raise_for_status()
                    return
                except (httpx.HTTPError, httpx.TimeoutException):
                    if attempt == 1:
                        raise
```

**Step 4: 테스트 통과 확인**
```bash
docker compose exec backend pytest tests/test_redmine_client.py -v
# 예상: PASSED (2/2)
```

**Step 5: 커밋**
```bash
git add backend/app/services/redmine_client.py backend/tests/test_redmine_client.py
git commit -m "feat: Redmine REST API 클라이언트 구현 (이슈 조회, 댓글 작성)"
```

**완료 기준**: 모킹된 Redmine API로 이슈 조회 및 댓글 작성 테스트 통과.

---

### Task 6: TF-IDF 기반 유사 이슈 검색 서비스 구현

**우선순위**: Must Have | **예상 소요**: 1.5일 | **담당**: 백엔드 담당 2명

**목표**: 이슈 제목+설명을 TF-IDF 벡터화하여 코사인 유사도로 상위 5개 이슈 추출

**파일**:
- 생성: `backend/app/services/similarity.py`
- 생성: `backend/tests/test_similarity.py`

**세부 단계**:

**Step 1: 테스트 먼저 작성**
```python
# backend/tests/test_similarity.py
from app.services.similarity import SimilarityService

def test_find_similar_issues_basic():
    """유사한 이슈가 상위로 반환되는지 확인"""
    service = SimilarityService(threshold=0.1)
    existing = [
        {"id": 1, "subject": "로그인 오류 발생", "description": "로그인 페이지에서 500 에러"},
        {"id": 2, "subject": "배포 파이프라인 실패", "description": "CI/CD 빌드 실패"},
        {"id": 3, "subject": "데이터베이스 연결 오류", "description": "DB 커넥션 타임아웃"},
    ]
    new_issue = {"id": 10, "subject": "로그인 실패 오류", "description": "로그인 시 에러 발생"}
    results = service.find_similar(new_issue, existing)
    assert len(results) > 0
    assert results[0]["id"] == 1  # 가장 유사한 이슈

def test_find_similar_issues_below_threshold():
    """임계값 이하는 반환되지 않음"""
    service = SimilarityService(threshold=0.9)
    existing = [{"id": 1, "subject": "완전히 다른 주제", "description": "관련 없는 내용"}]
    new_issue = {"id": 10, "subject": "로그인 오류", "description": "로그인 실패"}
    results = service.find_similar(new_issue, existing)
    assert len(results) == 0

def test_find_similar_max_results():
    """최대 5개까지만 반환"""
    service = SimilarityService(threshold=0.0, max_results=5)
    existing = [{"id": i, "subject": f"이슈 {i}", "description": "공통 내용 로그인 오류"} for i in range(10)]
    new_issue = {"id": 99, "subject": "이슈 관련", "description": "공통 내용"}
    results = service.find_similar(new_issue, existing)
    assert len(results) <= 5

def test_duplicate_detection():
    """유사도 90% 이상이면 중복 플래그"""
    service = SimilarityService(threshold=0.1, duplicate_threshold=0.9)
    # 동일 텍스트로 중복 시뮬레이션
    existing = [{"id": 1, "subject": "로그인 오류 발생 500에러", "description": "로그인 페이지 500 에러 발생"}]
    new_issue = {"id": 10, "subject": "로그인 오류 발생 500에러", "description": "로그인 페이지 500 에러 발생"}
    results = service.find_similar(new_issue, existing)
    assert results[0]["is_duplicate"] is True
```

**Step 2: 테스트 실패 확인**
```bash
docker compose exec backend pytest tests/test_similarity.py -v
# 예상: FAILED (모듈 없음)
```

**Step 3: `backend/app/services/similarity.py` 구현**
```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from app.config import settings

class SimilarityService:
    def __init__(
        self,
        threshold: float = None,
        duplicate_threshold: float = None,
        max_results: int = None
    ):
        self.threshold = threshold if threshold is not None else settings.similarity_threshold
        self.duplicate_threshold = duplicate_threshold if duplicate_threshold is not None else settings.duplicate_threshold
        self.max_results = max_results if max_results is not None else settings.max_similar_issues

    def _to_text(self, issue: dict) -> str:
        """이슈 제목 + 설명을 하나의 텍스트로 합침"""
        subject = issue.get("subject", "")
        description = issue.get("description", "") or ""
        return f"{subject} {description}".strip()

    def find_similar(self, new_issue: dict, existing_issues: list[dict]) -> list[dict]:
        """
        새 이슈와 기존 이슈 목록 간 유사도 계산 후 상위 N개 반환.
        반환 형식: [{"id": int, "subject": str, "score": float, "is_duplicate": bool}]
        """
        if not existing_issues:
            return []

        new_text = self._to_text(new_issue)
        existing_texts = [self._to_text(issue) for issue in existing_issues]
        corpus = [new_text] + existing_texts

        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3))
        try:
            tfidf_matrix = vectorizer.fit_transform(corpus)
        except ValueError:
            return []

        new_vec = tfidf_matrix[0]
        existing_vecs = tfidf_matrix[1:]
        scores = cosine_similarity(new_vec, existing_vecs).flatten()

        results = []
        for idx, score in enumerate(scores):
            if score >= self.threshold:
                issue = existing_issues[idx]
                results.append({
                    "id": issue["id"],
                    "subject": issue.get("subject", ""),
                    "score": float(score),
                    "is_duplicate": score >= self.duplicate_threshold
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[: self.max_results]
```

**Step 4: 테스트 통과 확인**
```bash
docker compose exec backend pytest tests/test_similarity.py -v
# 예상: PASSED (4/4)
```

**Step 5: 커버리지 확인**
```bash
docker compose exec backend pytest tests/test_similarity.py --cov=app/services/similarity --cov-report=term-missing
# 커버리지 80% 이상 목표
```

**Step 6: 커밋**
```bash
git add backend/app/services/similarity.py backend/tests/test_similarity.py
git commit -m "feat: TF-IDF 기반 유사 이슈 검색 서비스 구현"
```

**완료 기준**: 4개 단위 테스트 통과, 커버리지 80% 이상.

---

### Task 7: 폴링 폴백 구현

**우선순위**: Must Have | **예상 소요**: 0.5일 | **담당**: 백엔드 담당 1명

**목표**: `ISSUE_DETECTION_MODE=polling` 설정 시 1분마다 Redmine 신규 이슈 폴링

**파일**:
- 생성: `backend/app/services/poller.py`
- 수정: `backend/app/main.py` (lifespan 이벤트에 스케줄러 등록)

**세부 단계**:

**Step 1: `backend/app/services/poller.py` 작성**
```python
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.config import settings
from app.services.redmine_client import RedmineClient

logger = logging.getLogger(__name__)
_last_polled_at: datetime | None = None

async def poll_new_issues():
    """1분 이내 등록된 새 이슈 폴링"""
    global _last_polled_at
    client = RedmineClient()
    since = _last_polled_at or (datetime.utcnow() - timedelta(minutes=1))
    _last_polled_at = datetime.utcnow()
    logger.info(f"[폴링] {since.isoformat()} 이후 신규 이슈 확인 중...")
    # 실제 처리는 웹훅 핸들러와 동일한 process_webhook 호출 예정

def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(poll_new_issues, "interval", minutes=1, id="issue_poller")
    return scheduler
```

**Step 2: `backend/app/main.py` lifespan 수정**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.routers import webhook

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.issue_detection_mode == "polling":
        from app.services.poller import create_scheduler
        scheduler = create_scheduler()
        scheduler.start()
    yield
    # 종료 시 정리 작업 (필요 시 추가)

app = FastAPI(title="Redmine Helper", version="1.0.0", lifespan=lifespan)
app.include_router(webhook.router)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

**Step 3: 동작 확인**
```bash
# .env에서 ISSUE_DETECTION_MODE=polling 설정 후
docker compose up
# 로그에서 "[폴링] ... 신규 이슈 확인 중..." 메시지 1분마다 출력 확인
```

**Step 4: 커밋**
```bash
git add backend/app/services/poller.py backend/app/main.py
git commit -m "feat: APScheduler 폴링 폴백 구현 (ISSUE_DETECTION_MODE=polling)"
```

**완료 기준**: `ISSUE_DETECTION_MODE=polling` 설정 시 1분마다 폴링 로그가 출력된다.

---

### Task 8: 웹훅 수신 → 유사도 계산 → DB 저장 파이프라인 연동

**우선순위**: Must Have | **예상 소요**: 1일 | **담당**: 백엔드 담당 2명

**목표**: 웹훅 수신 후 백그라운드에서 유사 이슈 검색 → DB 저장 → 로그 출력 전체 흐름 동작

**파일**:
- 생성: `backend/app/services/analysis_pipeline.py`
- 수정: `backend/app/routers/webhook.py` (process_webhook 함수를 파이프라인 호출로 교체)
- 생성: `backend/tests/test_pipeline.py`

**세부 단계**:

**Step 1: 테스트 먼저 작성**
```python
# backend/tests/test_pipeline.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.analysis_pipeline import run_analysis

@pytest.mark.asyncio
async def test_pipeline_saves_to_db():
    """파이프라인 실행 시 analysis_history DB에 저장되는지 확인"""
    mock_issues = [{"id": 1, "subject": "유사 이슈", "description": "내용"}]
    mock_similar = [{"id": 1, "subject": "유사 이슈", "score": 0.8, "is_duplicate": False}]

    with patch("app.services.analysis_pipeline.RedmineClient") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.get_issues = AsyncMock(return_value=mock_issues)

        with patch("app.services.analysis_pipeline.SimilarityService") as MockSimilarity:
            mock_sim = MockSimilarity.return_value
            mock_sim.find_similar = MagicMock(return_value=mock_similar)

            mock_db = MagicMock()
            await run_analysis(issue_id=10, project_id=1, subject="로그인 오류", description="에러 발생", db=mock_db)

            assert mock_db.add.called
            assert mock_db.commit.called
```

**Step 2: 테스트 실패 확인**
```bash
docker compose exec backend pytest tests/test_pipeline.py -v
# 예상: FAILED (모듈 없음)
```

**Step 3: `backend/app/services/analysis_pipeline.py` 구현**
```python
import logging
from sqlalchemy.orm import Session
from app.services.redmine_client import RedmineClient
from app.services.similarity import SimilarityService
from app.models.analysis import AnalysisHistory, DuplicateDetection
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

async def run_analysis(issue_id: int, project_id: int, subject: str, description: str, db: Session = None):
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
            ai_summary=None
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

        # 5. 로그 출력
        logger.info(f"[분석 완료] 이슈 #{issue_id} — 유사 이슈 {len(similar)}건 발견")
        for item in similar:
            dup_flag = " [중복 의심]" if item["is_duplicate"] else ""
            logger.info(f"  - #{item['id']} {item['subject']} (유사도: {item['score']:.1%}){dup_flag}")

    except Exception as e:
        logger.error(f"[분석 실패] 이슈 #{issue_id}: {e}")
        error_record = AnalysisHistory(
            issue_id=issue_id,
            project_id=project_id,
            status="failed",
            error_message=str(e)
        )
        _db.add(error_record)
        _db.commit()
    finally:
        if db is None:
            _db.close()
```

**Step 4: `backend/app/routers/webhook.py` 수정** — `process_webhook` 함수를 `run_analysis` 호출로 교체
```python
from app.services.analysis_pipeline import run_analysis

async def process_webhook(issue_id: int, project_id: int, subject: str, description: str):
    await run_analysis(issue_id=issue_id, project_id=project_id, subject=subject, description=description)
```

**Step 5: 테스트 통과 확인**
```bash
docker compose exec backend pytest tests/test_pipeline.py -v
# 예상: PASSED
```

**Step 6: 전체 테스트 실행 및 커버리지 확인**
```bash
docker compose exec backend pytest --cov=app --cov-report=term-missing
# 목표: 전체 커버리지 80% 이상
```

**Step 7: 커밋**
```bash
git add backend/app/services/analysis_pipeline.py backend/app/routers/webhook.py backend/tests/test_pipeline.py
git commit -m "feat: 웹훅 수신 → 유사도 계산 → DB 저장 파이프라인 연동"
```

**완료 기준**: 웹훅 전송 후 서버 로그에 유사 이슈 목록이 출력되고, SQLite에 `analysis_history` 레코드가 생성된다.

---

### Task 9: E2E 통합 검증

**우선순위**: Must Have | **예상 소요**: 0.5일 | **담당**: 전체 팀

**목표**: `docker compose up` 후 실제 웹훅 요청으로 전체 흐름 동작 확인

**세부 단계**:

**Step 1: 전체 서비스 재빌드 및 마이그레이션 실행**
```bash
docker compose up --build -d
docker compose exec backend alembic upgrade head
```

**Step 2: 테스트 웹훅 요청 전송**
```bash
# 시그니처 생성 스크립트 (scripts/send_test_webhook.sh)
SECRET="your_webhook_secret"
PAYLOAD='{"action":"opened","issue":{"id":999,"subject":"로그인 페이지 500 오류","description":"로그인 시 500 에러가 발생합니다.","project":{"id":1,"name":"테스트 프로젝트"}}}'
SIG=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')
curl -X POST http://localhost:8000/webhook/redmine \
  -H "Content-Type: application/json" \
  -H "X-Redmine-Token: $SIG" \
  -d "$PAYLOAD"
```

**Step 3: 로그 확인**
```bash
docker compose logs backend | grep "분석"
# 예상 출력:
# [분석 완료] 이슈 #999 — 유사 이슈 N건 발견
# - #123 로그인 오류 관련 이슈 (유사도: 78.3%)
```

**Step 4: DB 레코드 확인**
```bash
docker compose exec backend python -c "
from app.db.session import SessionLocal
from app.models.analysis import AnalysisHistory
db = SessionLocal()
records = db.query(AnalysisHistory).all()
for r in records:
    print(f'#{r.issue_id} status={r.status} similar={r.similar_issues}')
"
```

**Step 5: 잘못된 토큰 요청 확인**
```bash
curl -X POST http://localhost:8000/webhook/redmine \
  -H "Content-Type: application/json" \
  -H "X-Redmine-Token: wrong_token" \
  -d '{"action":"opened","issue":{"id":1,"subject":"test","description":"","project":{"id":1,"name":"test"}}}'
# 예상: {"detail":"Invalid webhook token"} (HTTP 401)
```

**Step 6: 최종 커밋**
```bash
git add scripts/
git commit -m "chore: E2E 테스트용 웹훅 전송 스크립트 추가"
```

**완료 기준**: Sprint 1 Definition of Done 전체 항목 충족.

---

## 의존성 및 리스크

### 태스크 간 의존성

```
Task 1 (Docker 환경)
    ├── Task 2 (FastAPI 구조)
    │       ├── Task 3 (DB 스키마)
    │       ├── Task 4 (웹훅 엔드포인트)
    │       ├── Task 5 (Redmine 클라이언트)
    │       └── Task 6 (유사도 서비스)
    │               └── Task 7 (폴링 폴백)
    └── Task 8 (파이프라인 연동) ← Task 3, 4, 5, 6 완료 필요
            └── Task 9 (E2E 검증) ← Task 8 완료 필요
```

### 리스크 및 대응 방안

| 리스크 | 가능성 | 영향도 | 대응 방안 |
|--------|--------|--------|-----------|
| Redmine 웹훅 설정 권한 부족 | 중간 | 높음 | Sprint 1 착수 전 Redmine 봇 계정 및 웹훅 설정 권한 확인. 폴링 폴백으로 우선 검증 가능 |
| 한국어 TF-IDF 품질 저조 | 중간 | 중간 | 공백 토큰화 + char_wb n-gram으로 우선 대응. 품질 미달 시 Sprint 2에서 임베딩 도입 |
| SQLite WAL 모드 동시성 | 낮음 | 낮음 | Sprint 1에서는 단일 웹훅 처리 위주, WAL 모드는 Sprint 4에서 강화 |
| httpx 비동기 + BackgroundTasks 누수 | 낮음 | 중간 | 각 요청마다 AsyncClient 컨텍스트 매니저로 리소스 해제 보장 |

### 사전 준비 사항 (착수 전 확인 필요)

- ⬜ Redmine 인스턴스 접근 가능 여부 확인
- ⬜ Redmine 봇 계정 생성 (댓글 작성 권한 포함)
- ⬜ Redmine API Key 발급 (최소 권한: 이슈 조회 + 댓글 작성)
- ⬜ Redmine 웹훅 플러그인 설치 여부 확인 (버전에 따라 다름)
- ⬜ Redmine 최소 지원 버전 확인 (4.1+ 권장)
- ⬜ Docker 개발 환경 세팅 (Docker Desktop 또는 Colima)

---

## 팀 역할 분담 (10명 기준)

| 역할 | 인원 | 담당 태스크 |
|------|------|-------------|
| 인프라 담당 | 1명 | Task 1 (Docker 환경), 사전 준비 사항 확인 |
| 백엔드 리드 | 1명 | Task 2 (프로젝트 구조), Task 8 (파이프라인 연동) |
| 백엔드 개발 | 4명 | Task 3 (DB), Task 4 (웹훅), Task 5 (Redmine 클라이언트), Task 6 (유사도) |
| 백엔드 개발 | 1명 | Task 7 (폴링 폴백) |
| QA | 1명 | Task 9 (E2E 검증), 전체 테스트 리뷰 |
| PM/아키텍트 | 2명 | 코드 리뷰, 스프린트 진행 관리, Sprint 2 준비 |

---

## 완료 기준 (Definition of Done)

| # | 항목 | 확인 방법 |
|---|------|-----------|
| 1 | ⬜ `docker compose up` 후 Redmine 웹훅 테스트 요청 → 유사 이슈 목록이 서버 로그에 출력 | `docker compose logs backend \| grep 분석` |
| 2 | ⬜ 시크릿 토큰이 틀린 요청 → HTTP 401 반환 | `curl` 테스트 (Task 9 Step 5) |
| 3 | ⬜ SQLite `analysis_history` 레코드 생성 확인 | Task 9 Step 4 DB 조회 |
| 4 | ⬜ 단위 테스트 커버리지 80% 이상 (유사도, 웹훅 파싱) | `pytest --cov` 결과 |
| 5 | ⬜ 잘못된 페이로드 요청 → HTTP 400 반환 | 단위 테스트 |
| 6 | ⬜ `ISSUE_DETECTION_MODE=polling` 시 1분마다 폴링 로그 출력 | `docker compose logs` 확인 |

---

## 예상 산출물

| 산출물 | 경로 | 설명 |
|--------|------|------|
| Docker 환경 파일 | `docker-compose.yml`, `backend/Dockerfile`, `.env.example` | 단일 명령 배포 환경 |
| FastAPI 백엔드 | `backend/app/` | 프로젝트 구조, 라우터, 서비스, 모델 |
| DB 마이그레이션 | `backend/alembic/` | Alembic 초기 마이그레이션 |
| 웹훅 엔드포인트 | `backend/app/routers/webhook.py` | HMAC 검증 + BackgroundTasks |
| Redmine 클라이언트 | `backend/app/services/redmine_client.py` | httpx 비동기 클라이언트 |
| 유사도 서비스 | `backend/app/services/similarity.py` | TF-IDF 코사인 유사도 |
| 분석 파이프라인 | `backend/app/services/analysis_pipeline.py` | 전체 처리 흐름 |
| 단위 테스트 | `backend/tests/` | 커버리지 80% 이상 |
| 테스트 스크립트 | `scripts/send_test_webhook.sh` | E2E 검증용 |

---

## 다음 스프린트 준비 사항

Sprint 1 완료 후 Sprint 2 착수 전 확인해야 할 사항:

- ⬜ Claude API Key 발급 및 `.env` 등록
- ⬜ TF-IDF 유사도 품질 평가 (실제 이슈 데이터로 테스트)
- ⬜ 유사도 임계값 조정 여부 결정 (기본 0.3이 적절한지 확인)
- ⬜ Redmine 커스텀 필드 목록 확인 (카테고리 태깅용)
- ⬜ 댓글 작성 형식 최종 확정 (PRD 4.2 기준)
