import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
SECRET = "test_secret"


def make_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_webhook_valid_request():
    payload = {
        "action": "opened",
        "issue": {
            "id": 1,
            "subject": "테스트 이슈",
            "description": "내용",
            "project": {"id": 1, "name": "프로젝트"},
        },
    }
    body = json.dumps(payload).encode()
    sig = make_signature(body, SECRET)
    response = client.post(
        "/webhook/redmine",
        content=body,
        headers={"X-Redmine-Token": sig, "Content-Type": "application/json"},
    )
    assert response.status_code == 202


def test_webhook_invalid_token():
    payload = {
        "action": "opened",
        "issue": {
            "id": 1,
            "subject": "테스트",
            "description": "",
            "project": {"id": 1, "name": "프로젝트"},
        },
    }
    body = json.dumps(payload).encode()
    response = client.post(
        "/webhook/redmine",
        content=body,
        headers={"X-Redmine-Token": "wrong_token", "Content-Type": "application/json"},
    )
    assert response.status_code == 401


def test_webhook_non_issue_created_event():
    payload = {
        "action": "updated",
        "issue": {
            "id": 1,
            "subject": "테스트",
            "description": "",
            "project": {"id": 1, "name": "프로젝트"},
        },
    }
    body = json.dumps(payload).encode()
    sig = make_signature(body, SECRET)
    response = client.post(
        "/webhook/redmine",
        content=body,
        headers={"X-Redmine-Token": sig, "Content-Type": "application/json"},
    )
    assert response.status_code == 200  # 무시하되 에러는 아님
