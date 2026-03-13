import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app as application
from app.db.session import Base, get_db
from app.models.analysis import AnalysisHistory  # noqa: F401 — Base.metadata 등록
import app.models.settings  # noqa: F401
from app.dependencies.auth import get_current_user

# StaticPool로 인메모리 SQLite 연결 공유
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(application)


@pytest.fixture(autouse=True)
def setup_db_and_overrides():
    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_current_user] = lambda: {"sub": "dashboard"}
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    application.dependency_overrides.clear()


def test_get_analysis_list_empty():
    """분석 이력이 없을 때 빈 목록 반환"""
    response = client.get("/api/analysis")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_get_analysis_list_with_data():
    """분석 이력이 있을 때 목록 반환"""
    db = TestingSessionLocal()
    record = AnalysisHistory(
        issue_id=1, project_id=1, status="success",
        similar_issues=[{"id": 2, "subject": "유사 이슈", "score": 0.8, "is_duplicate": False}],
        ai_summary="요약 내용", created_at=datetime.utcnow()
    )
    db.add(record)
    db.commit()
    db.close()

    response = client.get("/api/analysis")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["issue_id"] == 1


def test_get_analysis_detail():
    """분석 상세 조회"""
    db = TestingSessionLocal()
    record = AnalysisHistory(
        issue_id=5, project_id=2, status="success",
        similar_issues=[{"id": 3, "subject": "테스트", "score": 0.75, "is_duplicate": False}],
        ai_summary="AI 요약 텍스트", created_at=datetime.utcnow()
    )
    db.add(record)
    db.commit()
    record_id = record.id
    db.close()

    response = client.get(f"/api/analysis/{record_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["issue_id"] == 5
    assert data["ai_summary"] == "AI 요약 텍스트"


def test_get_analysis_detail_not_found():
    """존재하지 않는 분석 ID 조회 시 404"""
    response = client.get("/api/analysis/99999")
    assert response.status_code == 404


def test_get_analysis_pagination():
    """페이지네이션 동작 확인"""
    db = TestingSessionLocal()
    for i in range(10):
        db.add(AnalysisHistory(issue_id=i, project_id=1, status="success", created_at=datetime.utcnow()))
    db.commit()
    db.close()

    response = client.get("/api/analysis?page=1&page_size=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    assert data["total"] == 10
