# Redmine 웹훅 설정 가이드

**대상**: Redmine Helper를 웹훅 모드로 연동하려는 관리자

---

## 웹훅 지원 버전 확인

| Redmine 버전 | 웹훅 지원 |
|-------------|---------|
| 5.0 이상 | ✅ 기본 내장 (플러그인 불필요) |
| 4.1 ~ 4.2 | ✅ [redmine_webhook](https://github.com/suer/redmine_webhook) 플러그인 필요 |
| 4.0 이하 | ❌ 폴링 모드 권장 |

웹훅 미지원 환경: `.env`에서 `ISSUE_DETECTION_MODE=polling` 으로 전환하면 1분 주기 폴링으로 동작합니다.

---

## Redmine 5.0+ 내장 웹훅 설정

### 1. 관리자 로그인

Redmine에 관리자 계정으로 로그인합니다.

### 2. 웹훅 메뉴 접근

```
관리 (Administration) → 웹훅 (Webhooks)
```

### 3. 신규 웹훅 추가

**새 웹훅 (New Webhook)** 버튼 클릭 후 다음 값 입력:

| 필드 | 값 |
|------|-----|
| **URL** | `http://<서버IP>:8080/webhook/redmine` |
| **시크릿 (Secret)** | `.env`의 `WEBHOOK_SECRET` 값 |
| **이벤트** | `이슈 생성 (issue_created)` 체크 |
| **프로젝트** | 전체 또는 특정 프로젝트 선택 |

> **중요**: URL은 Redmine 서버가 접근 가능한 주소여야 합니다. Docker 환경에서는 `host.docker.internal:8080` 또는 실제 서버 IP를 사용하세요.

### 4. 저장 및 테스트

저장 후 **테스트 전송 (Send test)** 버튼으로 연결을 확인합니다.

---

## redmine_webhook 플러그인 설정 (Redmine 4.x)

### 1. 플러그인 설치

```bash
cd /path/to/redmine/plugins
git clone https://github.com/suer/redmine_webhook.git
cd /path/to/redmine
bundle install
bundle exec rake redmine:plugins:migrate RAILS_ENV=production
```

Redmine 재시작:
```bash
touch tmp/restart.txt
```

### 2. 플러그인 설정

```
관리 → 플러그인 → Redmine Webhook → 설정
```

| 필드 | 값 |
|------|-----|
| **Webhook URL** | `http://<서버IP>:8080/webhook/redmine` |

### 3. 프로젝트별 활성화

웹훅을 적용할 각 프로젝트에서:

```
프로젝트 → 설정 → 모듈 → "Webhook" 체크
```

그 후 해당 프로젝트의 **Webhook 탭**에서 URL을 설정합니다.

---

## HMAC 서명 검증

Redmine Helper는 웹훅 요청의 `X-Redmine-Token` 헤더를 HMAC-SHA256으로 검증합니다.

- Redmine 5.0+는 **시크릿** 필드 입력 시 자동으로 HMAC 서명
- redmine_webhook 플러그인은 HMAC 미지원 → `.env`에서 `WEBHOOK_SECRET`을 빈 값으로 설정

```env
# redmine_webhook 플러그인 사용 시
WEBHOOK_SECRET=
```

> ⚠️ `WEBHOOK_SECRET`이 비어 있으면 서명 검증을 건너뜁니다. 내부 네트워크에서만 접근 가능하도록 방화벽 설정을 권장합니다.

---

## 연동 확인

### 서버 로그에서 수신 확인

```bash
docker compose logs -f backend | grep webhook
# {"time": "...", "level": "INFO", "message": "[Webhook] 이슈 #123 수신, 분석 시작"}
```

### 헬스체크로 Redmine 연결 상태 확인

```bash
curl http://localhost:8080/health
# {"status": "ok", "checks": {"db": "ok", "redmine": "configured", "claude": "configured"}}
```

---

## 자주 발생하는 문제

| 증상 | 원인 | 해결 방법 |
|------|------|-----------|
| 웹훅 전송 후 응답 없음 | 방화벽 차단 | 서버 IP:8080 포트 개방 확인 |
| 401 Unauthorized | 시크릿 토큰 불일치 | Redmine 웹훅 시크릿과 `.env` `WEBHOOK_SECRET` 일치 확인 |
| 202 응답이지만 분석 없음 | `issue_created` 이벤트 미선택 | 웹훅 이벤트 설정 확인 |
| `REDMINE_API_ERROR` 로그 | API Key 권한 부족 | Redmine API Key에 이슈 조회/수정 권한 확인 |
| 댓글 미작성 | `ENABLE_AUTO_COMMENT=false` | `.env` 값 변경 후 컨테이너 재시작 |

---

## Redmine API Key 권한 설정

Redmine Helper에 사용할 API Key 계정에 필요한 권한:

| 기능 | 필요 권한 |
|------|---------|
| 이슈 목록 조회 | 프로젝트 멤버 (이슈 보기) |
| 이슈 댓글 작성 | 이슈 추가/수정 |
| 커스텀 필드 업데이트 | 이슈 수정 |

전용 봇 계정 생성을 권장합니다 (`redmine-helper-bot` 등).

API Key 확인 방법:
```
로그인 → 내 계정 (My Account) → API 액세스 키 (API access key)
```
