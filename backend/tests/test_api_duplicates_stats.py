import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app as application
from app.db.session import Base, get_db
from app.models.analysis import AnalysisHistory, DuplicateDetection  # noqa: F401
import app.models.settings  # noqa: F401
from app.dependencies.auth import get_current_user

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


def test_get_duplicates_empty():
    """중복 감지 이력이 없을 때 빈 목록"""
    response = client.get("/api/duplicates")
    assert response.status_code == 200
    assert response.json() == []


def test_get_duplicates_with_data():
    """중복 감지 이력 반환"""
    db = TestingSessionLocal()
    db.add(DuplicateDetection(source_issue_id=1, target_issue_id=2, similarity_score=0.95, created_at=datetime.utcnow()))
    db.commit()
    db.close()

    response = client.get("/api/duplicates")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["source_issue_id"] == 1
    assert data[0]["similarity_score"] == 0.95


def test_get_stats():
    """통계 API 반환 구조 확인"""
    db = TestingSessionLocal()
    db.add(AnalysisHistory(issue_id=1, project_id=1, status="success", created_at=datetime.utcnow()))
    db.add(AnalysisHistory(issue_id=2, project_id=1, status="failed", created_at=datetime.utcnow()))
    db.add(AnalysisHistory(issue_id=3, project_id=1, status="no_similar", created_at=datetime.utcnow()))
    db.add(DuplicateDetection(source_issue_id=4, target_issue_id=5, similarity_score=0.92, created_at=datetime.utcnow()))
    db.commit()
    db.close()

    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_analyzed"] == 3
    assert data["total_success"] == 1
    assert data["total_failed"] == 1
    assert data["total_no_similar"] == 1
    assert data["total_duplicates"] == 1
    assert round(data["success_rate"], 2) == 0.33


def test_rerun_analysis():
    """수동 재분석 요청 수락"""
    response = client.post("/api/analysis/rerun", json={"issue_id": 10, "project_id": 1})
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
