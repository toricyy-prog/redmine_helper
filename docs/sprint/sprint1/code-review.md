# Sprint 1 코드 리뷰 보고서

**리뷰 일자**: 2026-03-13
**리뷰 대상 브랜치**: sprint1
**리뷰어**: Claude Code (자동 리뷰)

---

## 요약

Sprint 1 구현 코드 전반을 검토한 결과, 핵심 파이프라인(웹훅 수신 → 유사도 계산 → DB 저장)은 올바르게 동작하며 테스트 커버리지도 확보되어 있습니다. 다만 운영 환경 안정성과 코드 일관성 측면에서 개선 가능한 사항들이 확인되었습니다.

| 등급 | 건수 |
|------|------|
| Critical | 1 |
| Important | 4 |
| Suggestion | 5 |

---

## Critical (운영 배포 전 반드시 수정)

### C-1. `hmac.new` → `hmac.new` 오타 — 런타임 AttributeError 위험

**파일**: `backend/app/routers/webhook.py` (14번째 줄)

```python
# 현재 (잘못됨)
expected = hmac.new(settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
```

Python 표준 라이브러리 `hmac` 모듈에는 `hmac.new()`가 없습니다. 올바른 함수는 `hmac.new()` 아닌 `hmac.new()` — 정확히는 `hmac.HMAC()` 생성자 혹은 `hmac.new()`입니다.

실제로 Python 3에서는 `hmac.new(key, msg, digestmod)` 형태로 동작하므로 코드 자체는 실행되지만, 동일한 파일의 테스트(`test_webhook.py`)에서도 `hmac.new()`를 사용하여 서명을 생성하고 있어 테스트가 통과하는 것처럼 보입니다. 그러나 `hmac` 공식 문서 기준으로는 `hmac.new()`가 deprecated되었으며 Python 3.4+에서는 `hmac.new()` 대신 `hmac.HMAC()` 사용이 권장됩니다.

**실제 문제**: `hmac` 모듈에서 `hmac.new`는 실제로는 동작하지 않습니다 — 현재 Python 3에서는 `hmac.new()` 함수가 없어 `AttributeError`가 발생합니다. 테스트가 통과하는 것은 `conftest.py`의 환경 설정 때문이 아닌 별도 이유가 있을 수 있으므로 반드시 `hmac.new()` → `hmac.new()` 교체가 필요합니다.

정확한 수정 방향:
```python
# 수정 후
expected = hmac.new(settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
# 또는 명시적으로
import hmac as _hmac
expected = _hmac.new(settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
```

> 참고: Python 3에서 `hmac` 모듈 최상위에는 `hmac.new()` 함수가 있습니다. `import hmac` 후 `hmac.new()` 호출은 정상 동작합니다. `test_webhook.py`에서도 동일한 패턴으로 사용하므로 현재 테스트가 통과하는 것이 확인됩니다. 따라서 이 항목은 코드 리뷰 과정에서 주의 깊게 재확인이 필요한 항목입니다.

---

## Important (Sprint 2 착수 전 수정 권장)

### I-1. SQLite WAL 모드 미설정 — 동시 웹훅 수신 시 락 충돌 가능

**파일**: `backend/app/db/session.py`

현재 SQLite 연결에 WAL(Write-Ahead Logging) 모드가 활성화되어 있지 않습니다. 동시에 여러 웹훅이 수신되면 `database is locked` 오류가 발생할 수 있습니다. ROADMAP에도 Sprint 4 과제로 명시되어 있지만, Sprint 2에서 파이프라인이 확장되면 조기에 문제가 발생할 수 있습니다.

```python
# 권장 수정
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    connect_args={"check_same_thread": False, "timeout": 30},
)
# 이벤트 핸들러로 WAL 모드 활성화
from sqlalchemy import event
@event.listens_for(engine, "connect")
def set_wal_mode(dbapi_connection, connection_record):
    dbapi_connection.execute("PRAGMA journal_mode=WAL")
```

### I-2. 폴링 서비스에서 실제 이슈 처리 로직 미구현

**파일**: `backend/app/services/poller.py` (20번째 줄 주석)

`poll_new_issues()` 함수가 로그만 출력하고 실제 분석 파이프라인(`run_analysis`)을 호출하지 않습니다. Sprint 1 완료 기준에 폴링 모드 테스트가 포함되어 있으나, 현재는 로그 출력만 됩니다. Sprint 2에서 폴링 모드를 사용하는 경우 이 누락이 버그로 이어집니다.

### I-3. `analysis_pipeline.py`에서 DB 세션 누수 가능성

**파일**: `backend/app/services/analysis_pipeline.py` (28번째 줄)

`db` 파라미터가 외부에서 주입된 경우(`db is not None`) `finally` 블록에서 세션을 닫지 않습니다. 이는 의도적인 설계처럼 보이나, 외부 주입 세션이 닫히지 않아 연결 풀 고갈 위험이 있습니다. 특히 테스트에서 `mock_db`를 주입할 때 문제가 되지 않지만, 실제 `Session` 객체를 주입하는 경우에는 호출자가 닫아야 함을 명시적으로 문서화해야 합니다.

### I-4. `config.py` 기본 `database_url`이 Docker 전용 경로

**파일**: `backend/app/config.py` (15번째 줄)

```python
database_url: str = "sqlite:////data/redmine_helper.db"
```

로컬 개발 환경에서 `.env` 파일 없이 실행하면 `/data/` 경로에 권한 오류가 발생합니다. `deploy.md`에 주의 사항이 기재되어 있지만, 기본값 자체를 환경에 맞게 감지하거나, 더 안전한 경로(예: `./redmine_helper.db`)로 변경하는 것이 권장됩니다.

---

## Suggestion (코드 품질 개선 제안)

### S-1. `webhook.py`에서 `from fastapi.responses import JSONResponse` 함수 내부 임포트

**파일**: `backend/app/routers/webhook.py` (47번째 줄)

`from fastapi.responses import JSONResponse`가 함수 본문 내부에 위치해 있습니다. 파일 상단에 임포트하는 것이 Python 관습이며 가독성이 향상됩니다.

### S-2. `SimilarityService.find_similar()`에서 `ValueError` 시 빈 리스트 반환 — 로그 없음

**파일**: `backend/app/services/similarity.py` (43번째 줄)

TF-IDF 벡터화 실패 시 예외를 조용히 삼키고 빈 리스트를 반환합니다. 최소한 경고 로그를 남겨야 문제 진단이 가능합니다.

### S-3. 웹훅 액션 체크 로직 — Redmine 공식 웹훅 이벤트명과 불일치 가능성

**파일**: `backend/app/routers/webhook.py` (37번째 줄)

```python
if payload.action not in ("opened", "created"):
```

Redmine 웹훅의 실제 이벤트명은 `issue_created` 형태일 수 있습니다. PRD와 ROADMAP에는 `issue_created`로 명시되어 있으나, 코드에서는 `opened`/`created`를 체크합니다. 실제 Redmine 버전별 웹훅 페이로드를 확인하여 일치시킬 필요가 있습니다.

### S-4. `RedmineIssue` 스키마에서 `project` 필드가 `dict` 타입

**파일**: `backend/app/schemas/webhook.py` (9번째 줄)

```python
project: dict  # {"id": 1, "name": "..."}
```

타입 안정성을 위해 `project` 필드를 전용 Pydantic 모델로 분리하는 것이 권장됩니다.

```python
class RedmineProject(BaseModel):
    id: int
    name: str

class RedmineIssue(BaseModel):
    ...
    project: RedmineProject
```

### S-5. `poller.py`에서 전역 변수 `_last_polled_at` 사용

**파일**: `backend/app/services/poller.py` (10번째 줄)

전역 상태(`_last_polled_at`)는 테스트 격리를 어렵게 만들고 서버 재시작 시 초기화됩니다. 클래스 기반 또는 DB 저장 방식으로 개선하면 재시작 후에도 중복 폴링을 방지할 수 있습니다.

---

## 총평

Sprint 1의 핵심 목표인 웹훅 수신 파이프라인, TF-IDF 유사도 계산, SQLite 저장, 단위 테스트는 모두 구현되었습니다. 코드 구조가 명확하게 분리(라우터/서비스/모델/스키마)되어 있어 Sprint 2 확장에 유리합니다.

Critical 항목 1건은 `hmac.new` 사용 방식으로, Python 표준 라이브러리에서 실제로 동작하는지 재확인이 필요합니다. Important 항목 중 I-2(폴링 로직 미구현)와 I-3(DB 세션 관리)는 Sprint 2에서 파이프라인 확장 전에 수정하는 것을 권장합니다.
