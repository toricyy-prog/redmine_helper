# Sprint 3 코드 리뷰 보고서

**리뷰어**: code-reviewer 에이전트
**리뷰 대상**: Sprint 3 구현 (`sprint3` 브랜치)
**리뷰 일시**: 2026-03-13
**커밋 범위**: `6d904c5` ~ `1c0110c`

---

## 전체 평가

Sprint 3에서 JWT 인증 미들웨어, REST API, Vue.js 3 프론트엔드, Alembic 마이그레이션까지 설계한 범위를 완전히 구현했습니다. 계층 분리(router / dependency / model / schema), 인메모리 DB 기반 테스트 픽스처, TypeScript 타입 활용 등 전체적으로 프로젝트 표준을 잘 준수하고 있습니다.

---

## Critical (반드시 수정)

없음.

---

## Important (수정 권장)

### 1. `AppSettings.id` 유일성 보장 부재 (백엔드)

**파일**: `backend/app/models/settings.py`

`id = Column(Integer, primary_key=True, default=1)` 로 선언되어 있지만, SQLAlchemy ORM 레벨의 `default=1` 은 새 인스턴스를 생성할 때 Python 레벨에서 1을 주입하므로, 동시에 두 개의 `AppSettings()` 객체를 생성하면 PK 충돌이 발생합니다. `_get_or_create_settings` 함수에서 `db.query(AppSettings).first()` 로 먼저 조회하여 중복 생성을 방지하고 있어 현재는 문제가 없지만, 경쟁 조건(race condition) 가능성이 잠재합니다.

**권장 수정**: `id` 컬럼을 자동증가로 두거나, `CheckFirst` 패턴에 `SELECT ... FOR UPDATE` 형태의 명시적 잠금을 Sprint 4에서 추가하는 것을 권장합니다.

### 2. `enable_auto_comment` 컬럼 타입 불일치 (백엔드)

**파일**: `backend/app/models/settings.py`, `backend/app/routers/api.py`

DB에 `String(10)` 으로 `"true"/"false"` 문자열로 저장하고, 읽을 때 `== "true"` 비교로 bool 변환합니다. 같은 의미를 `Boolean` 컬럼으로 일관되게 관리하는 것이 더 명확합니다. 현재 로직은 동작하지만 향후 DB 직접 조회 시 혼동을 줄 수 있습니다.

**권장 수정**: Sprint 4 마이그레이션에서 `Boolean` 타입으로 전환하거나, 최소한 상수(`TRUTHY = "true"`)로 추출하여 하드코딩된 문자열 비교를 제거합니다.

### 3. `_run_reanalysis` 내부 함수 에러 핸들링 범위 (백엔드)

**파일**: `backend/app/routers/api.py` (131~149 라인)

`except Exception` 블록에서 `logging.getLogger(__name__).error(...)` 만 수행하고 재분석 결과를 DB에 기록하지 않습니다. 재분석 실패 시 사용자가 대시보드에서 실패 상태를 확인할 방법이 없습니다.

**권장 수정**: 실패 시 `AnalysisHistory` 레코드에 `status="failed"`, `error_message=str(e)` 를 업데이트하는 로직을 추가합니다.

### 4. Axios 요청 인터셉터에서 Pinia 스토어 미사용 (프론트엔드)

**파일**: `frontend/src/api/client.ts`

`apiClient.interceptors.request.use` 에서 `localStorage.getItem('access_token')` 을 직접 읽고 있습니다. Pinia `useAuthStore`를 사용하는 것이 토큰 상태를 단일 출처(Single Source of Truth)로 관리하는 Vue.js 권장 패턴에 더 부합합니다. 현재는 localStorage와 스토어가 사실상 동기화되어 있어 버그는 없지만, 향후 토큰 갱신 로직 추가 시 불일치가 발생할 수 있습니다.

---

## Suggestions (개선 제안)

### 1. 비밀번호 비교 타이밍 공격 방어

**파일**: `backend/app/routers/auth.py` (29라인)

`req.password != settings.dashboard_password` 단순 문자열 비교는 타이밍 공격(timing attack)에 취약합니다. 팀 내부 도구이므로 실제 위험도는 낮지만, `secrets.compare_digest` 사용을 권장합니다.

### 2. `GET /api/duplicates` 페이지네이션 미적용

**파일**: `backend/app/routers/api.py` (65~77라인)

중복 감지 목록은 하드코딩 `limit(100)` 만 적용되어 페이지네이션이 없습니다. 분석 이력(`/api/analysis`)과 API 일관성을 맞추기 위해 동일한 페이지네이션 파라미터 추가를 고려합니다.

### 3. `AnalysisHistoryItem.Config` 구식 패턴

**파일**: `backend/app/schemas/analysis.py`

Pydantic v2에서는 `class Config: from_attributes = True` 대신 `model_config = ConfigDict(from_attributes=True)` 사용을 권장합니다. 현재 동작하지만 미래 호환성을 위해 교체를 권장합니다.

### 4. 프론트엔드 오류 처리 세분화 부족

**파일**: `frontend/src/views/SettingsView.vue`, `LoginView.vue`

`catch` 블록에서 오류 종류를 구분하지 않고 단일 메시지만 표시합니다. 네트워크 오류와 서버 오류(4xx/5xx)를 구분하여 사용자에게 더 명확한 피드백을 제공할 수 있습니다.

### 5. 프론트엔드 `counter.ts` 스토어 미사용 파일

**파일**: `frontend/src/stores/counter.ts`

Vite 프로젝트 초기화 시 생성된 기본 스토어 파일로, 실제 코드에서 사용되지 않습니다. 불필요한 파일 제거를 권장합니다.

---

## 잘된 점

- **JWT 미들웨어 설계**: `HTTPBearer(auto_error=False)` + 명시적 401 반환으로 FastAPI 패턴을 정확히 따름
- **테스트 독립성**: `StaticPool` + `autouse` 픽스처로 각 테스트 간 DB 상태 격리가 잘 구현됨
- **Pinia 스토어 구조**: `useAuthStore` 가 로그인/로그아웃 상태를 중앙 관리하고 Vue Router 가드와 연동됨
- **Alembic 마이그레이션**: `down_revision` 체인이 올바르게 연결되어 있고 `downgrade()` 구현 완료
- **설정 API 유효성 검사**: `SettingsUpdateRequest` 에 Pydantic `Field(ge=0.1, le=1.0)` 범위 제약이 적용됨
- **Docker 멀티스테이지 빌드**: Vue.js 빌드 아티팩트를 FastAPI `static/` 으로 병합하는 구조가 깔끔함

---

## 종합 의견

Sprint 3 구현은 계획한 전체 기능(백엔드 7개 API + 프론트엔드 5개 화면 + 인증 + 마이그레이션)을 완성도 높게 구현했습니다. Critical 이슈는 없으며, Important 이슈 중 `_run_reanalysis` 에러 핸들링 개선(이슈 3번)은 Sprint 4에서 안정화 작업 시 함께 처리할 것을 권장합니다. 나머지 Important/Suggestion 항목들은 Sprint 4 백로그로 추가하여 관리합니다.
