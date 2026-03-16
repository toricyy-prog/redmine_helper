# 🗺️ 프로젝트 로드맵 — Redmine Helper

**작성일**: 2026-03-13
**기준 PRD**: docs/PRD.md v1.0
**팀 규모**: 개발자 10명
**대상 환경**: Redmine 프로젝트 30개, Docker 컨테이너 배포

---

## 📊 프로젝트 현황 대시보드

| 항목 | 내용 |
|------|------|
| 전체 진행률 | 75% (Sprint 1, 2, 3 완료) |
| 현재 Phase | Phase 3 — 안정화 및 운영 품질 향상 |
| 다음 마일스톤 | Sprint 4 종료: 안정화 및 운영 준비 |
| 전체 예상 기간 | 약 8주 (Sprint 1 ~ Sprint 4) |

---

## 진행 상태 범례

- ✅ 완료
- 🔄 진행 중
- 📋 예정
- ⏸️ 보류

---

## 🏗️ 기술 아키텍처 결정 사항

| 영역 | 결정 사항 | 이유 |
|------|-----------|------|
| 백엔드 프레임워크 | FastAPI (Python) | 비동기 처리, 웹훅 수신에 적합; 팀 친숙도 |
| 프론트엔드 | Vue.js 3 (Composition API) | 가벼운 SPA, 대시보드 구현에 적합 |
| DB | SQLite | 단일 서버 배포, 팀 규모(10명) 대비 충분한 성능 |
| AI 엔진 | Claude API (claude-3-5-sonnet 권장) | PRD 지정 |
| 유사도 알고리즘 | Sprint 1에서 키워드 TF-IDF로 시작 → Sprint 2에서 임베딩 방식 도입 검토 | 초기 빠른 구현 후 품질 개선 전략 |
| 이슈 감지 방식 | Redmine 웹훅 우선, 폴링 폴백 지원 | 웹훅 미지원 버전 호환성 확보 |
| 배포 | Docker Compose 단일 명령 | 운영 단순화 |
| 인증 | 단순 비밀번호 (대시보드) + Redmine API Key (.env) | 팀 내부용, 복잡한 계정 관리 불필요 |

---

## 📅 Phase별 상세 계획

---

### Phase 1: 기반 인프라 및 핵심 자동화 (Sprint 1 ~ Sprint 2)

> **목표**: 웹훅 수신 → 유사 이슈 검색 → AI 요약 → 댓글 자동 작성의 핵심 파이프라인을 동작시킨다.

---

#### ✅ Sprint 1: 프로젝트 초기화 + 웹훅 수신 + 유사 이슈 검색 (2026-03-13 ~ 2026-03-13) — 완료

**Sprint Goal**: Redmine 새 이슈 등록 시 웹훅을 수신하여 유사 이슈 목록을 검색하고 콘솔에 출력할 수 있다.

##### 작업 목록

**인프라 & 프로젝트 구조 (Must Have)**
- ✅ **Docker Compose 환경 구성**: `docker-compose.yml`, `Dockerfile` 작성
  - FastAPI 컨테이너, Vue.js 빌드 컨테이너 분리
  - `.env.example` 파일 작성 (REDMINE_URL, REDMINE_API_KEY, CLAUDE_API_KEY, WEBHOOK_SECRET, DASHBOARD_PASSWORD)
  - `docker compose up` 으로 전체 서비스 기동 확인
- ✅ **FastAPI 프로젝트 구조 초기화**: 디렉토리 구조, 라우터, 의존성 주입 기반 설정
  - `app/main.py`, `app/routers/`, `app/services/`, `app/models/`, `app/db/` 구조 수립
  - SQLite 연결 및 Alembic 마이그레이션 초기 설정
- ✅ **SQLite 스키마 설계 및 초기 마이그레이션**
  - `analysis_history` 테이블: issue_id, project_id, status, similar_issues(JSON), ai_summary, created_at, error_message
  - `duplicate_detections` 테이블: source_issue_id, target_issue_id, similarity_score, created_at

**웹훅 수신 (Must Have)**
- ✅ **Redmine 웹훅 수신 엔드포인트 구현**: `POST /webhook/redmine`
  - 시크릿 토큰 HMAC 검증 미들웨어
  - `issue_created` 이벤트 파싱 (이슈 ID, 제목, 설명, 프로젝트 ID 추출)
  - 잘못된 페이로드/토큰 불일치 시 400/401 반환
  - 수신 즉시 202 Accepted 반환 후 백그라운드 작업으로 처리 (FastAPI BackgroundTasks)
- ✅ **폴링 폴백 구현 (설정으로 전환 가능)**: APScheduler로 1분 주기 폴링
  - 환경 변수 `ISSUE_DETECTION_MODE=webhook|polling` 으로 전환

**Redmine REST API 클라이언트 (Must Have)**
- ✅ **Redmine API 클라이언트 구현** (`app/services/redmine_client.py`)
  - 이슈 목록 조회: `GET /issues.json` (프로젝트 필터, 최근 1년 범위 기본값)
  - 이슈 상세 조회: `GET /issues/{id}.json` (댓글 포함)
  - 댓글 작성: `POST /issues/{id}/notes.json`
  - 커스텀 필드 업데이트 지원 (카테고리 태깅용)
  - httpx AsyncClient 기반, 재시도 1회 로직 포함

**유사 이슈 검색 (Must Have)**
- ✅ **키워드 기반 유사도 계산 구현** (`app/services/similarity.py`)
  - TF-IDF 방식으로 이슈 제목+설명 벡터화 (scikit-learn)
  - 코사인 유사도 계산
  - 상위 5개 이슈 추출, 임계값(기본 0.3) 이하 제외
  - 유사도 90% 이상 → 중복 감지 플래그 설정
- ✅ **이슈 검색 서비스 연동**: 웹훅 수신 → Redmine에서 기존 이슈 조회 → 유사도 계산 → 결과 로그 출력

##### 완료 기준 (Definition of Done)
- ✅ `docker compose up` 후 Redmine 웹훅 테스트 요청을 보내면 유사 이슈 목록이 서버 로그에 출력된다.
- ✅ 시크릿 토큰이 틀린 요청은 401을 반환한다.
- ✅ SQLite에 `analysis_history` 레코드가 생성된다.
- ✅ 단위 테스트: 유사도 계산 함수, 웹훅 파싱 함수 커버리지 80% 이상

##### 기술 고려사항
- 첫 웹훅 수신 시 30개 프로젝트 전체 이슈를 조회하면 속도 문제 발생 가능 → 웹훅 페이로드의 프로젝트 ID로 범위 한정
- TF-IDF 한국어 처리: `konlpy` 또는 공백 토큰화로 시작, 품질 부족 시 Sprint 2에서 개선

---

#### ✅ Sprint 2: AI 요약 + 댓글 자동 작성 + 이슈 분류/태깅 (2026-03-27 ~ 2026-03-13) — 완료

**Sprint Goal**: 유사 이슈 검색 결과를 Claude API로 요약하고 원본 이슈에 댓글을 자동 작성한다. 이슈 자동 분류도 동작한다.

##### 작업 목록

**AI 요약 + 댓글 작성 (Must Have)**
- ✅ **Claude API 클라이언트 구현** (`app/services/claude_client.py`)
  - `anthropic` SDK 사용, 비동기 호출
  - 유사 이슈 댓글/해결책 수집 후 2000자 이내로 프롬프트 구성
  - 타임아웃 30초 설정
  - API 실패 시 1회 재시도 → 실패 시 요약 없이 이슈 목록만 반환
- ✅ **댓글 자동 작성 서비스 구현** (`app/services/comment_writer.py`)
  - PRD 지정 댓글 형식 준수: `[Redmine Helper 자동 분석]` 헤더, 해결 방법 요약, 참고 이슈 링크(유사도 % 포함)
  - 중복 감지 시 별도 경고 댓글 형식 사용
  - 동일 이슈에 Redmine Helper 댓글이 이미 존재하면 재작성 방지 (기존 댓글 확인 로직)
  - 수동 재분석 요청 시에는 기존 댓글 업데이트 (force 파라미터)
- ✅ **전체 파이프라인 통합**: 웹훅 수신 → 검색 → AI 요약 → 댓글 작성 → DB 저장 → 2분 이내 완료 확인
- ✅ **에러 핸들링 강화**: Claude API 실패, Redmine API 실패, 유사 이슈 없음 각 케이스 처리 및 DB 상태 기록

**이슈 자동 분류/태깅 (Should Have)**
- ✅ **카테고리 분류 서비스 구현** (`app/services/classifier.py`)
  - `.env` 또는 설정 파일에서 카테고리 목록 로드
  - Claude API로 이슈 → 카테고리 분류 (신뢰도 점수 포함)
  - 신뢰도 임계값(기본 0.7) 미만 시 태깅 보류 → 대시보드 검토 항목으로 표기
- ✅ **Redmine 커스텀 필드 업데이트**: 분류 결과를 Redmine 이슈 커스텀 필드에 반영

**유사도 알고리즘 개선 검토 (Should Have)**
- ⬜ **임베딩 방식 PoC**: Sprint 3으로 이관 (TF-IDF 품질 검증 후 도입 결정 예정)

##### 완료 기준 (Definition of Done)
- ✅ Redmine에 새 이슈를 등록하면 2분 이내에 AI 요약 댓글이 자동으로 작성된다. (ENABLE_AUTO_COMMENT=true 시)
- ✅ Claude API 호출 실패 시 유사 이슈 목록만 댓글로 작성된다.
- ✅ 이슈 등록 시 카테고리가 자동 분류되어 Redmine 커스텀 필드에 반영된다.
- ✅ 동일 이슈에 댓글 중복 작성이 발생하지 않는다.
- ✅ 통합 테스트: 웹훅 → 댓글 작성 전체 흐름 테스트 (pytest + httpx TestClient) — 31개 전부 PASSED

##### 기술 고려사항
- Claude API 요금 관리: 이슈 내용 2000자 제한 및 캐싱 전략 수립 필요
- 댓글 작성 실패 시 재시도 큐 도입 고려 (Sprint 3에서 필요 시 추가)

---

### Phase 2: 웹 대시보드 (Sprint 3)

> **목표**: 분석 이력, 중복 감지 결과, 통계를 확인할 수 있는 Vue.js 대시보드를 제공한다.

---

#### ✅ Sprint 3: Vue.js 대시보드 구현 (2026-04-10 ~ 2026-03-13) — 완료

**Sprint Goal**: 팀원이 브라우저에서 분석 이력, 중복 감지 이력, 통계, 설정을 확인하고 수동 재분석을 실행할 수 있다.

##### 작업 목록

**백엔드 API (Must Have)**
- ✅ **대시보드용 REST API 구현**
  - `GET /api/analysis` — 최근 분석 이력 목록 (최대 100건, 페이지네이션)
  - `GET /api/analysis/{id}` — 분석 상세 (원본 이슈 정보, 유사 이슈 목록, AI 요약)
  - `GET /api/duplicates` — 중복 감지 이력 목록
  - `GET /api/stats` — 카테고리별 이슈 수, 중복 감지 수, 성공/실패 통계
  - `POST /api/analysis/rerun` — 수동 재분석 실행 (이슈 ID 지정)
  - `GET /api/settings`, `PUT /api/settings` — 임계값, 카테고리 목록 조회/수정
- ✅ **대시보드 인증 미들웨어**: 환경 변수 `DASHBOARD_PASSWORD` 기반 Bearer 토큰 인증

**Vue.js 프론트엔드 (Must Have)**
- ✅ **Vue.js 3 프로젝트 초기화**: Vite 빌드, Vue Router, Pinia, Axios 설정
- ✅ **대시보드 홈 화면 구현** (`/`)
  - 최근 분석 이슈 목록 테이블: 이슈 번호, 제목, 처리 상태(성공/실패/유사없음), 처리 시각
  - 통계 요약 카드: 오늘 처리 건수, 중복 감지 건수, 성공률
  - Redmine 이슈 링크 클릭 시 새 탭으로 이동
- ✅ **분석 상세 화면 구현** (`/analysis/:id`)
  - 원본 이슈 정보 (번호, 제목, 설명)
  - 유사 이슈 목록 (유사도 퍼센트 바 포함)
  - AI 요약 내용 (마크다운 렌더링)
  - 작성된 댓글 미리보기
  - 수동 재분석 버튼
- ✅ **중복 감지 목록 화면 구현** (`/duplicates`)
  - 중복 의심 이슈 쌍 목록
  - 유사도 점수, 감지 일시
  - 원본 이슈 / 중복 의심 이슈 각각 Redmine 링크 제공
- ✅ **설정 화면 구현** (`/settings`)
  - 유사도 임계값 슬라이더 (0.1 ~ 1.0)
  - 중복 감지 임계값 슬라이더 (기본 0.9)
  - 카테고리 목록 편집 (추가/삭제)
  - 저장 버튼

**비기능 (Should Have)**
- ✅ **로그인 화면 구현** (`/login`): DASHBOARD_PASSWORD 입력 → JWT 발급 → localStorage 저장
- ✅ **반응형 레이아웃**: 최소 1280px 데스크탑 기준, 모바일 고려 불필요

##### 완료 기준 (Definition of Done)
- ✅ `docker compose up` 후 `http://localhost:8080` 접속 시 로그인 화면이 표시된다.
- ✅ 로그인 후 대시보드 홈에서 최근 100건의 분석 이력을 확인할 수 있다.
- ✅ 분석 상세 화면에서 원본 이슈 링크, 유사 이슈 목록, AI 요약이 표시된다.
- ✅ 수동 재분석 버튼 클릭 시 재분석이 실행되고 결과가 갱신된다.
- ✅ 설정 화면에서 임계값 변경 후 저장하면 이후 분석에 적용된다.

##### 기술 고려사항
- Vue.js는 Docker 빌드 시 정적 파일로 컴파일하여 FastAPI의 `static/` 로 서빙 (별도 Nginx 불필요)
- API Key는 설정 화면에서 마스킹 처리 (입력 시 `****` 표시)

---

### Phase 3: 안정화 및 운영 품질 향상 (Sprint 4)

> **목표**: 운영 환경에서 발생할 수 있는 엣지 케이스를 처리하고, 모니터링과 유지보수성을 강화한다.

---

#### Sprint 4: 안정화, 에러 처리 강화, 운영 준비 (2026-04-24 ~ 2026-05-07)

**Sprint Goal**: 운영 환경에서 안정적으로 동작하며, 장애 발생 시 빠르게 진단할 수 있다.

##### 작업 목록

**안정성 & 에러 처리 (Must Have)**
- ⬜ **재시도 큐 도입**: Redmine 댓글 작성 실패 시 최대 3회 재시도 (지수 백오프)
- ⬜ **타임아웃 전체 적용**: Redmine API 10초, Claude API 30초 하드 타임아웃
- ⬜ **에러 로그 구조화**: JSON 포맷 로그, 에러 코드/메시지/이슈 ID 포함
- ⬜ **대시보드 실패 항목 표시 개선**: 실패 원인 코드별 메시지 (REDMINE_API_ERROR, CLAUDE_API_ERROR, NO_SIMILAR_ISSUES 등)
- ⬜ **반복 댓글 방지 안정성 검증**: 동시 웹훅 수신 시 중복 댓글 방지 (DB 트랜잭션 락)

**운영 편의성 (Should Have)**
- ⬜ **헬스체크 엔드포인트**: `GET /health` — Redmine 연결, Claude API Key 유효성, DB 상태 반환
- ⬜ **분석 이력 자동 정리**: 90일 이상 된 분석 이력 자동 삭제 (설정 가능)
- ⬜ **임베딩 캐싱**: 동일 이슈 재분석 시 임베딩 재계산 방지 (SQLite 캐시)
- ⬜ **Docker 이미지 최적화**: 멀티스테이지 빌드로 이미지 크기 최소화

**테스트 강화 (Should Have)**
- ⬜ **통합 테스트 suite 완성**: pytest + TestClient로 전체 웹훅 파이프라인 커버
- ⬜ **Redmine API 모킹**: `respx` 또는 `responses` 라이브러리로 외부 API 모킹
- ⬜ **부하 테스트**: 10개 이슈 동시 웹훅 수신 시 2분 이내 처리 확인 (Locust)

**문서화 (Should Have)**
- ⬜ **README.md 작성**: 설치 방법, `.env` 설정 가이드, Redmine 웹훅 설정 방법
- ⬜ **Redmine 웹훅 설정 가이드**: 최소 지원 버전, 설정 단계별 스크린샷 포함
- ⬜ **운영 가이드**: 로그 확인 방법, 장애 대응 절차

##### 완료 기준 (Definition of Done)
- `GET /health` 가 모든 의존성 상태를 반환한다.
- 동시 웹훅 10개 수신 시 중복 댓글이 발생하지 않는다.
- 통합 테스트 전체 통과.
- README.md를 보고 신규 팀원이 30분 이내에 환경을 구성할 수 있다.

---

## 🔗 의존성 맵

```
Sprint 1 (인프라 + 웹훅 + Redmine API + 유사도 검색)
    │
    ▼
Sprint 2 (Claude API + 댓글 작성 + 자동 분류)
    │
    ▼
Sprint 3 (Vue.js 대시보드 — 백엔드 API Sprint 1~2에 의존)
    │
    ▼
Sprint 4 (안정화 — Sprint 1~3 전체에 의존)
```

**주요 의존성**:
- 댓글 자동 작성 → Redmine API 클라이언트 (Sprint 1 완료 필요)
- AI 요약 → Claude API 클라이언트 + 유사 이슈 검색 결과 (Sprint 1 완료 필요)
- 대시보드 → 분석 이력 DB 스키마 + REST API (Sprint 1~2 완료 필요)
- 수동 재분석 → 전체 파이프라인 통합 (Sprint 2 완료 필요)

---

## ⚠️ 리스크 및 완화 전략

| 리스크 | 가능성 | 영향도 | 완화 전략 |
|--------|--------|--------|-----------|
| Redmine 버전이 웹훅 미지원 | 중간 | 높음 | Sprint 1에서 폴링 폴백 동시 구현, 환경 변수로 전환 |
| Claude API 응답 지연/장애 | 낮음 | 중간 | 30초 타임아웃, 실패 시 요약 없이 이슈 목록만 댓글 작성 |
| 유사도 알고리즘 품질 부족 (TF-IDF) | 중간 | 중간 | Sprint 2에서 임베딩 PoC 진행, 채택 여부 결정 |
| SQLite 동시성 문제 (여러 웹훅 동시 수신) | 중간 | 중간 | WAL 모드 활성화, DB 트랜잭션 락 적용 (Sprint 4) |
| Redmine API Key 권한 부족 | 낮음 | 높음 | 초기 설정 단계에서 필요 권한 목록 문서화, 헬스체크로 조기 감지 |
| 임베딩 저장 전략 미결 | 높음 | 낮음 | Sprint 2 PoC 결과에 따라 SQLite BLOB 또는 별도 처리 결정 |
| 한국어 TF-IDF 품질 | 중간 | 중간 | konlpy 또는 공백 토큰화, Sprint 2에서 임베딩으로 대체 검토 |

---

## 📈 마일스톤

| 마일스톤 | 목표일 | 내용 |
|---------|--------|------|
| M1: 핵심 파이프라인 동작 | ~~2026-03-26~~ **2026-03-13 완료** | 웹훅 수신 → 유사 이슈 검색 → 로그 출력 (Sprint 1 완료) |
| M2: AI 자동 댓글 MVP | ~~2026-04-09~~ **2026-03-13 완료** | 실제 Redmine에 AI 요약 댓글 자동 작성 (Sprint 2 완료) |
| M3: 대시보드 오픈 | ~~2026-04-23~~ **2026-03-13 완료** | 브라우저에서 분석 이력 확인 및 수동 재분석 가능 (Sprint 3 완료) |
| M4: 운영 안정화 | 2026-05-07 | 통합 테스트 완료, 운영 문서화 완성 (Sprint 4 완료) |

---

## 🔮 향후 계획 (Backlog — MVP 이후)

아래 항목은 PRD 범위 외이거나 MVP 이후 검토할 기능입니다.

| 기능 | 설명 | 우선순위 |
|------|------|---------|
| 임베딩 벡터 검색 도입 | TF-IDF 대비 높은 유사도 품질, pgvector 또는 Chroma DB 전환 | 높음 |
| Slack/Teams 알림 연동 | 중복 이슈 감지 시 채널 알림 발송 | 중간 |
| 이슈 담당자 자동 추천 | 과거 이슈 처리 이력 기반으로 담당자 추천 | 중간 |
| 다국어 지원 | 영어 이슈 처리 (Claude는 지원하나 TF-IDF 개선 필요) | 낮음 |
| 이슈 자동 닫기 | 중복 이슈를 자동으로 닫는 옵션 (현재 PRD에서 제외) | 낮음 |
| PostgreSQL 전환 | 이슈 수 급증 시 SQLite 한계 대응 | 낮음 |
| 분석 품질 피드백 | 팀원이 AI 요약 품질에 👍/👎 평가 → 프롬프트 개선 데이터 | 낮음 |

---

## 📝 미결 사항 추적

| 항목 | 내용 | 결정 기한 | 담당 |
|------|------|-----------|------|
| 유사도 알고리즘 | TF-IDF로 시작, Sprint 2 PoC 후 임베딩 도입 여부 결정 | Sprint 2 리뷰 (2026-04-09) | 개발팀 |
| Redmine 최소 지원 버전 | 웹훅 지원 버전 확인 필요 (Redmine 4.1+ 권장) | Sprint 1 착수 전 | 인프라 담당 |
| 봇 계정 | 전용 Redmine 봇 계정 생성 여부 | Sprint 1 착수 전 | 프로젝트 관리자 |
| 임베딩 저장 전략 | SQLite BLOB vs 별도 벡터 DB | Sprint 2 리뷰 (2026-04-09) | 개발팀 |
| 다국어 지원 | 영어 이슈 처리 여부 | Backlog | 제품 오너 |
