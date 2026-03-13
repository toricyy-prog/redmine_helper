import os

# 테스트 실행 전 환경 변수 설정 (Docker 없이 로컬 테스트 지원)
os.environ.setdefault("REDMINE_URL", "http://localhost")
os.environ.setdefault("REDMINE_API_KEY", "test")
os.environ.setdefault("CLAUDE_API_KEY", "test")
os.environ.setdefault("WEBHOOK_SECRET", "test_secret")
os.environ.setdefault("DASHBOARD_PASSWORD", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("CATEGORY_LIST", "버그,기능요청,문의,성능,보안")
os.environ.setdefault("CLASSIFICATION_THRESHOLD", "0.7")
os.environ.setdefault("REDMINE_CATEGORY_FIELD_ID", "")

# 테스트용 DB 테이블 생성 (웹훅 BackgroundTask에서 DB 접근 시 테이블 없음 오류 방지)
from app.db.session import Base, engine  # noqa: E402
import app.models.analysis  # noqa: E402, F401

Base.metadata.create_all(bind=engine)
