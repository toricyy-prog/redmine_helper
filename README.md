# Redmine Helper

Redmine 이슈 등록 시 유사 이슈를 자동 검색하고 AI 요약을 제공하는 이슈 자동화 도우미입니다.

## 주요 기능

- **유사 이슈 자동 검색**: 새 이슈 등록 시 TF-IDF 기반으로 기존 유사 이슈를 즉시 탐색
- **AI 요약 댓글**: Claude API를 활용해 유사 이슈의 해결책을 요약하여 자동 댓글 작성
- **중복 이슈 감지**: 유사도 임계값 기반으로 중복 이슈를 감지하고 경고
- **이슈 자동 분류**: 카테고리 분류 및 태깅 자동화
- **웹 대시보드**: 분석 이력, 통계, 설정을 브라우저에서 확인

## 기술 스택

| 영역 | 기술 |
|------|------|
| 백엔드 | FastAPI, SQLAlchemy, SQLite, Alembic |
| AI | Claude API (claude-3-5-sonnet), TF-IDF (scikit-learn) |
| 프론트엔드 | Vue.js 3, Vite, Pinia, Vue Router, Axios |
| 인프라 | Docker Compose, uvicorn |

## 빠른 시작

### 사전 요구사항

- Docker & Docker Compose
- Redmine 인스턴스 (웹훅 지원 버전 권장: Redmine 4.1+)
- Claude API Key ([Anthropic Console](https://console.anthropic.com) 발급)

### 설치 및 실행

```bash
# 1. 저장소 클론
git clone https://github.com/your-org/redmine_helper.git
cd redmine_helper

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일 편집 (아래 설정 섹션 참고)

# 3. 서비스 시작
docker compose up --build -d

# 4. DB 마이그레이션
docker compose exec backend alembic upgrade head

# 5. 대시보드 접속
# http://localhost:8080
```

### 환경 변수 설정 (`.env`)

| 변수 | 설명 | 예시 |
|------|------|------|
| `REDMINE_URL` | Redmine 서버 주소 | `https://redmine.example.com` |
| `REDMINE_API_KEY` | Redmine API 키 (관리자 → 내 계정 → API 액세스 키) | `abc123...` |
| `CLAUDE_API_KEY` | Anthropic Claude API 키 | `sk-ant-...` |
| `WEBHOOK_SECRET` | 웹훅 HMAC 서명 검증 비밀 값 | `my-secret-token` |
| `DASHBOARD_PASSWORD` | 대시보드 로그인 비밀번호 | `secure-password` |
| `JWT_SECRET_KEY` | JWT 서명 키 (무작위 값 권장) | `random-secret-key` |
| `ENABLE_AUTO_COMMENT` | Redmine 댓글 자동 작성 활성화 | `true` / `false` (기본: `false`) |
| `ISSUE_DETECTION_MODE` | 이슈 감지 방식 | `webhook` / `polling` (기본: `webhook`) |

> ⚠️ **운영 환경**: `ENABLE_AUTO_COMMENT=false` (기본값)로 시작하여 동작 확인 후 `true`로 변경하세요.

### Redmine 웹훅 설정

Redmine에서 `관리 → 플러그인 → Webhook` (또는 Redmine 5.0+ 기본 웹훅):

1. **URL**: `http://<서버IP>:8080/webhook/redmine`
2. **시크릿 토큰**: `.env`의 `WEBHOOK_SECRET` 값
3. **트리거 이벤트**: `이슈 생성 (issue_created)` 선택

> 웹훅 미지원 시 `.env`에서 `ISSUE_DETECTION_MODE=polling` 으로 전환하면 1분 주기 폴링으로 동작합니다.

## 대시보드

| 화면 | 경로 | 설명 |
|------|------|------|
| 로그인 | `/login` | 비밀번호 입력 → JWT 발급 |
| 대시보드 홈 | `/` | 통계 카드 + 분석 이력 목록 |
| 분석 상세 | `/analysis/:id` | 유사 이슈, AI 요약, 수동 재분석 |
| 중복 감지 | `/duplicates` | 중복 의심 이슈 쌍 목록 |
| 설정 | `/settings` | 임계값, 카테고리 조회/수정 |

## 로컬 개발

```bash
# 백엔드 테스트 실행
cd backend
.venv\Scripts\pip install -r requirements.txt
pytest -v

# 프론트엔드 개발 서버
cd frontend
npm install
npm run dev   # http://localhost:5173 (백엔드 프록시: /api → localhost:8000)

# 백엔드 개발 서버
$env:DATABASE_URL = "sqlite:///./local.db"
$env:DASHBOARD_PASSWORD = "password"
cd backend
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

## 운영 가이드

### 로그 확인

```bash
docker compose logs -f backend
```

JSON 형식으로 출력됩니다:
```json
{"time": "2026-03-16T00:00:00Z", "level": "INFO", "logger": "app.services.analysis_pipeline", "message": "[Pipeline] 이슈 #123 분석 완료 — 유사 3건"}
```

### 헬스체크

```bash
curl http://localhost:8080/health
# {"status": "ok", "checks": {"db": "ok", "redmine": "configured", "claude": "configured"}}
```

### 분석 이력 정리

90일 이상 된 분석 이력은 매일 자정 자동 삭제됩니다.

### 주요 장애 대응

| 증상 | 원인 | 조치 |
|------|------|------|
| 웹훅 401 응답 | `WEBHOOK_SECRET` 불일치 | `.env` `WEBHOOK_SECRET` 확인 |
| 댓글 미작성 | `ENABLE_AUTO_COMMENT=false` | `.env` 값 `true`로 변경 후 재기동 |
| `REDMINE_API_ERROR` | Redmine 접속 불가 | `REDMINE_URL`, `REDMINE_API_KEY` 확인 |
| `CLAUDE_API_ERROR` | Claude API 한도/키 오류 | `CLAUDE_API_KEY` 확인, 크레딧 확인 |
| 대시보드 로그인 불가 | JWT 만료 또는 비밀번호 오류 | `DASHBOARD_PASSWORD` 확인 |
