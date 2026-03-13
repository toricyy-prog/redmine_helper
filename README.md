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

### 1. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일에 Redmine URL, API 키, Claude API 키 입력
```

### 2. Docker로 실행

```bash
docker compose up --build -d
docker compose exec backend alembic upgrade head
```

`http://localhost:8080` 접속 → 대시보드 로그인

### 3. 로컬 개발 환경

```bash
# 백엔드
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 프론트엔드 (별도 터미널)
cd frontend
npm install
npm run dev
# http://localhost:5173 접속
```

## 환경 변수 주요 항목

| 변수 | 설명 |
|------|------|
| `REDMINE_URL` | Redmine 서버 URL |
| `REDMINE_API_KEY` | Redmine REST API 키 |
| `CLAUDE_API_KEY` | Anthropic Claude API 키 |
| `WEBHOOK_SECRET` | 웹훅 HMAC 서명 검증 시크릿 |
| `DASHBOARD_PASSWORD` | 대시보드 로그인 비밀번호 |
| `ENABLE_AUTO_COMMENT` | 자동 댓글 작성 활성화 (기본: `false`) |

전체 항목은 `.env.example` 참고.
