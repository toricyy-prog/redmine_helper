# Sprint 2 배포 및 검증 가이드

**Sprint**: 2 — Claude API 요약 + 댓글 자동 작성 + 이슈 분류
**완료일**: 2026-03-13
**환경**: Docker 없이 PowerShell 기준 (로컬 Python 가상환경)

---

## 자동 검증 완료 항목

- ✅ **pytest 31개 전부 PASSED**
  - 테스트 경로: `backend/tests/`
  - 실행 결과: 31 passed, 0 failed, 0 errors
  - 커버리지 항목: ClaudeClient, CommentWriter, Classifier, AnalysisPipeline, 웹훅 파이프라인 통합 테스트

---

## 수동 검증 필요 항목

- ⬜ **ENABLE_AUTO_COMMENT=false 상태에서 댓글 미작성 확인** (기본값, 안전 모드)
- ⬜ **ENABLE_AUTO_COMMENT=true 설정 후 실제 Redmine 댓글 자동 작성 확인** (운영 준비 시)
- ⬜ **alembic upgrade head — category, comment_written 컬럼 추가 확인**
- ⬜ **Redmine 커스텀 필드 ID 설정 확인** (`REDMINE_CATEGORY_FIELD_ID`)

---

## 로컬 실행 방법 (PowerShell)

### 1. 가상환경 활성화 및 의존성 설치

```powershell
cd C:\work\source\redmine_helper\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. 환경 변수 설정 (.env)

`.env.example`을 복사하여 `.env` 생성 후 아래 항목 설정:

```
REDMINE_URL=http://your-redmine-host
REDMINE_API_KEY=your_redmine_api_key
CLAUDE_API_KEY=your_claude_api_key
WEBHOOK_SECRET=your_webhook_secret
DASHBOARD_PASSWORD=your_dashboard_password

# Sprint 2 신규 항목
ENABLE_AUTO_COMMENT=false          # true로 변경 시 실제 Redmine 댓글 작성
CATEGORIES=버그,기능요청,문의,성능,보안  # 카테고리 목록 (쉼표 구분)
CLASSIFICATION_THRESHOLD=0.7        # 분류 신뢰도 임계값
REDMINE_CATEGORY_FIELD_ID=          # Redmine 커스텀 필드 ID (미설정 시 업데이트 안 함)
```

### 3. DB 마이그레이션 실행

```powershell
# backend 디렉토리에서 실행
alembic upgrade head
```

확인 항목:
- `analysis_history` 테이블에 `category`, `category_confidence`, `comment_written` 컬럼 추가됨

### 4. 테스트 실행

```powershell
cd C:\work\source\redmine_helper\backend
pytest -v
```

기대 결과: `31 passed`

### 5. 서버 실행

```powershell
cd C:\work\source\redmine_helper\backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## ENABLE_AUTO_COMMENT 플래그 동작 확인

### 안전 모드 확인 (ENABLE_AUTO_COMMENT=false, 기본값)

1. `.env`에 `ENABLE_AUTO_COMMENT=false` 설정 (기본값)
2. 서버 실행 후 웹훅 테스트 요청 발송:

```powershell
$body = @{
    action = "opened"
    issue = @{
        id = 999
        subject = "테스트 이슈"
        description = "테스트 설명"
        project = @{ id = 1 }
    }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri "http://localhost:8000/webhook/redmine" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

3. 서버 로그에서 다음 메시지 확인:
   ```
   [CommentWriter] 이슈 #999: ENABLE_AUTO_COMMENT=false, 댓글 작성 건너뜀
   ```
4. Redmine에서 해당 이슈에 댓글이 작성되지 않았음을 확인

### 운영 모드 확인 (ENABLE_AUTO_COMMENT=true)

1. `.env`에 `ENABLE_AUTO_COMMENT=true` 설정
2. 서버 재시작
3. 실제 Redmine 프로젝트에 새 이슈 등록
4. 2분 이내에 아래 형식의 댓글이 자동 작성되는지 확인:
   ```
   ## [Redmine Helper 자동 분석]

   ### 해결 방법 요약
   (Claude API가 생성한 요약 내용)

   ### 참고 이슈
   - [#XX 이슈 제목](http://...) (유사도 XX%)

   ---
   _이 댓글은 Redmine Helper가 자동으로 작성하였습니다._
   ```

---

## alembic 마이그레이션 상세 확인

```powershell
# 마이그레이션 후 DB 스키마 확인
cd C:\work\source\redmine_helper\backend
python -c "
import sqlite3
conn = sqlite3.connect('local.db')
cursor = conn.execute('PRAGMA table_info(analysis_history)')
for row in cursor.fetchall():
    print(row)
conn.close()
"
```

Sprint 2에서 추가된 컬럼:
- `category` TEXT — 분류된 카테고리명
- `category_confidence` REAL — 분류 신뢰도 (0.0~1.0)
- `comment_written` INTEGER — 댓글 작성 여부 (0 또는 1)

---

## 이슈 및 주의사항

- `ENABLE_AUTO_COMMENT`는 기본값 `false`로 설정되어 있어 실수로 실제 Redmine에 댓글이 작성되는 것을 방지합니다.
- Claude API Key 없이 서버를 실행하면 AI 요약이 생성되지 않으며, 유사 이슈 목록만 댓글에 포함됩니다.
- `REDMINE_CATEGORY_FIELD_ID`가 설정되지 않으면 커스텀 필드 업데이트가 건너뜁니다 (정상 동작).
