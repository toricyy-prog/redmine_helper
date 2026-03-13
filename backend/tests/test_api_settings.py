import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app as application
from app.db.session import Base, get_db
import app.models.settings  # noqa: F401 — Base.metadata 등록
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


def test_get_settings_default():
    """설정 조회 — 기본값 반환"""
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["similarity_threshold"] == 0.3
    assert data["duplicate_threshold"] == 0.9
    assert data["max_similar_issues"] == 5


def test_update_settings():
    """설정 변경 후 조회 시 반영됨"""
    response = client.put("/api/settings", json={
        "similarity_threshold": 0.5,
        "category_list": ["버그", "기능 요청", "문의"]
    })
    assert response.status_code == 200

    get_resp = client.get("/api/settings")
    data = get_resp.json()
    assert data["similarity_threshold"] == 0.5
    assert "버그" in data["category_list"]


def test_update_settings_invalid_threshold():
    """임계값 범위 초과 시 422"""
    response = client.put("/api/settings", json={"similarity_threshold": 1.5})
    assert response.status_code == 422
