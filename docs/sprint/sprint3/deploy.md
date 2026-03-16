# Sprint 3 배포 가이드

**스프린트**: Sprint 3 — Vue.js 대시보드 + 백엔드 REST API
**작성일**: 2026-03-13

---

## 자동 검증 완료 항목

- ✅ 백엔드 API 전체 단위 테스트 통과 (47개 / 47개)
  - `pytest -v` → 47 passed, 3 warnings
  - test_auth.py (4개) — JWT 인증 미들웨어
  - test_api_analysis.py (5개) — 분석 이력 목록/상세 API
  - test_api_duplicates_stats.py (4개) — 중복 감지/통계/재분석 API
  - test_api_settings.py (3개) — 설정 조회/수정 API
  - test_main.py — 헬스체크 강화 (DB/Redmine/Claude 상태 포함)
- ✅ 프론트엔드 TypeScript 빌드 성공 (`npm run build` → `backend/static/` 출력)
- ✅ `GET /api/analysis` 토큰 없이 접근 → 401 반환 확인
- ✅ 폴링 모드 — `poll_new_issues()` 실제 Redmine API 조회 + 분석 파이프라인 실행
- ✅ 재분석 실패 시 DB에 `status="failed"` 기록
- ✅ `/health` 엔드포인트 — DB/Redmine/Claude 설정 상태 포함
- ✅ JSON 구조화 로그 (time/level/logger/message 필드)
- ✅ 분석 이력 90일 자동 정리 (매일 자정 APScheduler 실행)
- ✅ `enable_auto_comment` DB 컬럼 Boolean 타입으로 변경 (마이그레이션 0004)

---

## 수동 검증 필요 항목

### 1. Python 의존성 설치 (로컬 환경)

```powershell
cd backend
.venv\Scripts\pip install python-jose[cryptography]==3.3.0
```

### 2. Alembic 마이그레이션 (app_settings 테이블 + Boolean 컬럼 변경)

```powershell
# 로컬 환경 (local.db 사용)
$env:DATABASE_URL = "sqlite:///./local.db"
cd backend
.venv\Scripts\alembic upgrade head
# 0003: app_settings 테이블 생성
# 0004: enable_auto_comment 컬럼 String → Boolean 변경
```

Docker 환경:
```bash
docker compose exec backend alembic upgrade head
```

### 3. 로컬 서버 기동 및 API 확인

```powershell
$env:DATABASE_URL = "sqlite:///./local.db"
$env:DASHBOARD_PASSWORD = "your_password"
cd backend
.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. JWT 인증 API 테스트 (PowerShell)

```powershell
# 로그인 → JWT 발급
$LOGIN = Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/auth/login" `
  -ContentType "application/json" `
  -Body '{"password": "your_password"}'
$TOKEN = $LOGIN.access_token

# 분석 이력 조회
Invoke-RestMethod -Uri "http://localhost:8000/api/analysis" `
  -Headers @{ Authorization = "Bearer $TOKEN" }

# 통계 조회
Invoke-RestMethod -Uri "http://localhost:8000/api/stats" `
  -Headers @{ Authorization = "Bearer $TOKEN" }

# 설정 조회
Invoke-RestMethod -Uri "http://localhost:8000/api/settings" `
  -Headers @{ Authorization = "Bearer $TOKEN" }

# 토큰 없이 접근 → 401 확인
Invoke-RestMethod -Uri "http://localhost:8000/api/analysis" -ErrorAction SilentlyContinue
# 예상: 401 Unauthorized
```

### 5. Docker 전체 빌드 및 대시보드 확인

```bash
docker compose up --build -d
docker compose exec backend alembic upgrade head
```

- ⬜ `http://localhost:8080` 접속 → 로그인 화면 표시 확인
- ⬜ 올바른 비밀번호 입력 후 대시보드 홈으로 이동 확인
- ⬜ 대시보드 홈: 통계 카드 4개 + 분석 이력 테이블 표시
- ⬜ 분석 상세 화면: 원본 이슈 정보, 유사 이슈 목록, AI 요약 표시
- ⬜ 수동 재분석 버튼 동작 확인
- ⬜ 설정 화면: 임계값 슬라이더 조작 후 저장 → API 반영 확인

### 6. 프론트엔드 로컬 개발 서버 (선택)

```powershell
cd frontend
npm run dev
# http://localhost:5173 접속 (백엔드 프록시: /api → http://localhost:8000)
```

---

## 변경된 포트

| 항목 | Sprint 2 이전 | Sprint 3 |
|------|---------------|----------|
| 백엔드 HTTP 포트 | 8000 | **8080** |

> Docker Compose를 사용할 경우 `http://localhost:8080` 으로 접속합니다.
> 로컬 uvicorn 직접 실행 시에는 기존 8000 포트를 사용해도 무방합니다.

---

## 신규 환경 변수 (`.env` 추가 필요)

```env
# Sprint 3 추가
JWT_SECRET_KEY=your-secure-random-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
```

> `JWT_SECRET_KEY`는 반드시 무작위 비밀값으로 설정하세요. 기본값(`change-me-in-production`)은 프로덕션에서 사용 금지.

---

## 구현 완료 목록

- ✅ Task 1: JWT 인증 미들웨어 (POST /api/auth/login, Bearer 토큰 검증)
- ✅ Task 2: 분석 이력 API (GET /api/analysis, GET /api/analysis/{id})
- ✅ Task 3: 중복 감지/통계/재분석 API (GET /api/duplicates, GET /api/stats, POST /api/analysis/rerun)
- ✅ Task 4: 설정 API (GET/PUT /api/settings, app_settings DB 테이블)
- ✅ Task 5: Vue.js 3 프로젝트 초기화 및 Docker 멀티스테이지 빌드 통합
- ✅ Task 6: Axios API 클라이언트 및 Pinia 인증 스토어
- ✅ Task 7: 로그인 화면 (`/login`) + Vue Router 네비게이션 가드
- ✅ Task 8: 공통 레이아웃 + 대시보드 홈 (`/`)
- ✅ Task 9: 분석 상세 화면 (`/analysis/:id`) — 유사 이슈 바, AI 요약 마크다운
- ✅ Task 10: 중복 감지 목록 화면 (`/duplicates`)
- ✅ Task 11: 설정 화면 (`/settings`) — 임계값 슬라이더, 카테고리 편집
- ⬜ Task 12: E2E 통합 검증 (수동 — Docker 빌드 후 브라우저 확인)
