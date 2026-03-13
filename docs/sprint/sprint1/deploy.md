# Sprint 1 배포 및 검증 가이드

## 자동 검증 완료 항목

- ✅ 코드 구현 (Task 1~9 전체)
- ✅ 단위 테스트 파일 작성 완료 (test_main, test_webhook, test_redmine_client, test_similarity, test_pipeline)
- ✅ `conftest.py` — 로컬 테스트용 환경 변수 자동 설정

---

## 수동 검증 (Docker 없이 — PowerShell 기준)

### 1단계: Python 설치 확인

PowerShell에서:

```powershell
python --version
```

없으면 설치:

```powershell
winget install Python.Python.3.11
# 설치 후 PowerShell 재시작 필요
```

---

### 2단계: 가상환경 생성 및 의존성 설치

```powershell
cd C:\work\source\redmine_helper\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

### 3단계: 단위 테스트 실행

```powershell
# conftest.py가 환경 변수를 자동으로 설정해줌 (.env 파일 불필요)
pytest -v
```

**예상 출력:**

```
tests/test_main.py::test_health                                          PASSED
tests/test_webhook.py::test_webhook_valid_request                        PASSED
tests/test_webhook.py::test_webhook_invalid_token                        PASSED
tests/test_webhook.py::test_webhook_non_issue_created_event              PASSED
tests/test_similarity.py::test_find_similar_issues_basic                 PASSED
tests/test_similarity.py::test_find_similar_issues_below_threshold       PASSED
tests/test_similarity.py::test_find_similar_max_results                  PASSED
tests/test_similarity.py::test_duplicate_detection                       PASSED
tests/test_redmine_client.py::test_get_issues                            PASSED
tests/test_redmine_client.py::test_post_comment                          PASSED
tests/test_pipeline.py::test_pipeline_saves_to_db                        PASSED

11 passed in X.XXs
```

---

### 4단계: 커버리지 확인 (80% 이상 목표)

```powershell
pytest --cov=app --cov-report=term-missing
```

---

### 5단계: 서버 직접 실행

터미널 1에서:

```powershell
cd C:\work\source\redmine_helper\backend
.venv\Scripts\Activate.ps1

# 환경 변수 설정 (실제 값으로 변경)
$env:REDMINE_URL = "https://redmine.ubware.com"
$env:REDMINE_API_KEY = "your_api_key"
$env:WEBHOOK_SECRET = "your_webhook_secret"
# ⚠️ DATABASE_URL을 반드시 먼저 설정 — alembic.ini 기본값은 Docker 전용 경로(/data/)라 로컬에서 실패함
$env:DATABASE_URL = "sqlite:///./local.db"

# DB 마이그레이션
alembic upgrade head

# 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

브라우저에서 `http://localhost:8000/docs` 접속하여 Swagger UI 확인.

---

### 6단계: 웹훅 E2E 테스트

터미널 2에서 (서버 실행 중인 상태):

```powershell
# WEBHOOK_SECRET을 5단계에서 설정한 값으로 변경
$SECRET = "your_webhook_secret"
$PAYLOAD = '{"action":"opened","issue":{"id":999,"subject":"로그인 페이지 500 오류","description":"로그인 시 500 에러가 발생합니다.","project":{"id":1,"name":"테스트 프로젝트"}}}'

# HMAC-SHA256 서명 생성
$BYTES = [System.Text.Encoding]::UTF8.GetBytes($PAYLOAD)
$KEY   = [System.Text.Encoding]::UTF8.GetBytes($SECRET)
$HMAC  = New-Object System.Security.Cryptography.HMACSHA256
$HMAC.Key = $KEY
$SIG   = ($HMAC.ComputeHash($BYTES) | ForEach-Object { $_.ToString("x2") }) -join ""

# 정상 요청 (202 기대)
Invoke-RestMethod -Uri "http://localhost:8000/webhook/redmine" `
  -Method POST `
  -ContentType "application/json" `
  -Headers @{"X-Redmine-Token" = $SIG} `
  -Body $PAYLOAD

# 잘못된 토큰 요청 (401 기대)
Invoke-RestMethod -Uri "http://localhost:8000/webhook/redmine" `
  -Method POST `
  -ContentType "application/json" `
  -Headers @{"X-Redmine-Token" = "wrong_token"} `
  -Body $PAYLOAD
```

터미널 1 서버 로그에서 확인:

```
INFO: [분석 완료] 이슈 #999 — 유사 이슈 N건 발견
INFO:   - #123 로그인 오류 관련 이슈 (유사도: 78.3%)
```

---

### 7단계: DB 레코드 확인

```powershell
cd C:\work\source\redmine_helper\backend
.venv\Scripts\Activate.ps1

python -c "
from app.db.session import SessionLocal
from app.models.analysis import AnalysisHistory
import os; os.environ['DATABASE_URL'] = 'sqlite:///./local.db'
db = SessionLocal()
records = db.query(AnalysisHistory).all()
for r in records:
    print(f'#{r.issue_id} status={r.status} similar={r.similar_issues}')
"
```

---

### 8단계: 폴링 모드 테스트

```powershell
$env:ISSUE_DETECTION_MODE = "polling"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# 1분마다 "[폴링] ... 신규 이슈 확인 중..." 출력 확인
```

---

## 완료 기준 체크리스트

- ✅ `pytest -v` → 11개 테스트 전부 PASSED
- ✅ `pytest --cov=app` → 커버리지 80% 이상
- ✅ `http://localhost:8000/docs` Swagger UI 접속
- ✅ 웹훅 정상 요청 → HTTP 202, 서버 로그에 유사 이슈 출력
- ✅ 잘못된 토큰 요청 → HTTP 401 반환
- ✅ SQLite `analysis_history` 레코드 생성 확인
- ✅ `ISSUE_DETECTION_MODE=polling` 시 1분마다 폴링 로그 출력
