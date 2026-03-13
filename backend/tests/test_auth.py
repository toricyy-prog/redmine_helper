import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app as application
from app.db.session import Base, get_db
import app.models.analysis  # noqa: F401
import app.models.settings  # noqa: F401
from app.dependencies.auth import get_current_user

client = TestClient(application)


@pytest.fixture(autouse=True)
def clear_overrides():
    application.dependency_overrides.clear()
    yield
    application.dependency_overrides.clear()


def _make_test_db_override():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    return override


def test_login_success(monkeypatch):
    """올바른 비밀번호로 로그인 시 JWT 반환"""
    monkeypatch.setattr("app.routers.auth.settings.dashboard_password", "secret123")
    response = client.post("/api/auth/login", json={"password": "secret123"})
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_wrong_password(monkeypatch):
    """잘못된 비밀번호로 로그인 시 401 반환"""
    monkeypatch.setattr("app.routers.auth.settings.dashboard_password", "secret123")
    response = client.post("/api/auth/login", json={"password": "wrong"})
    assert response.status_code == 401


def test_protected_endpoint_without_token():
    """토큰 없이 보호된 엔드포인트 접근 시 401"""
    response = client.get("/api/analysis")
    assert response.status_code == 401


def test_protected_endpoint_with_valid_token(monkeypatch):
    """유효한 토큰으로 보호된 엔드포인트 접근 시 200"""
    application.dependency_overrides[get_db] = _make_test_db_override()

    monkeypatch.setattr("app.routers.auth.settings.dashboard_password", "secret123")
    login_resp = client.post("/api/auth/login", json={"password": "secret123"})
    token = login_resp.json()["access_token"]
    response = client.get("/api/analysis", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
