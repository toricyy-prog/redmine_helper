# Sprint 1 배포 및 검증 가이드

## 사전 준비

- ✅ 코드 구현 완료 (Task 1~9)
- ⬜ Docker Desktop 설치 및 실행 확인
- ⬜ `.env` 파일 생성 (`.env.example` 참고)

## 1단계: .env 파일 생성

```bash
cp .env.example .env
# .env 파일을 열어 실제 값으로 수정
# WEBHOOK_SECRET: 웹훅 테스트에 사용할 시크릿 (임의 문자열)
# REDMINE_URL, REDMINE_API_KEY: 실제 Redmine 인스턴스 정보 (없으면 임의값 입력 가능)
```

## 2단계: Docker 빌드 및 실행

```bash
docker compose up --build -d
```

## 3단계: DB 마이그레이션

```bash
docker compose exec backend alembic upgrade head
```

## 자동 검증 완료 항목

- ✅ 코드 구현 (Task 1~9 전체)
- ✅ 단위 테스트 파일 작성 완료 (test_main, test_webhook, test_redmine_client, test_similarity, test_pipeline)

## 수동 검증 필요 항목

### 4단계: 테스트 실행

```bash
docker compose exec backend pytest -v
docker compose exec backend pytest --cov=app --cov-report=term-missing
```

### 5단계: E2E 웹훅 테스트

```bash
# .env의 WEBHOOK_SECRET 값을 사용
./scripts/send_test_webhook.sh your_webhook_secret

# 로그 확인
docker compose logs backend | grep "분석"
```

### 6단계: DB 레코드 확인

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

### 7단계: 폴링 모드 테스트

```bash
# .env에서 ISSUE_DETECTION_MODE=polling 으로 변경 후
docker compose up --build -d
docker compose logs -f backend | grep "폴링"
# 1분마다 "[폴링] ... 신규 이슈 확인 중..." 출력 확인
```

## 완료 기준 체크리스트

- ⬜ `docker compose up` 후 `http://localhost:8000/docs` Swagger UI 접속
- ⬜ 웹훅 테스트 요청 → 유사 이슈 목록 서버 로그 출력
- ⬜ 잘못된 토큰 요청 → HTTP 401 반환
- ⬜ SQLite `analysis_history` 레코드 생성 확인
- ⬜ 단위 테스트 커버리지 80% 이상
- ⬜ `ISSUE_DETECTION_MODE=polling` 설정 시 1분마다 폴링 로그 출력
