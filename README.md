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

