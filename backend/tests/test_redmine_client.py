import httpx
import pytest
import respx

from app.services.redmine_client import RedmineClient


@pytest.mark.asyncio
@respx.mock
async def test_get_issues():
    respx.get("http://redmine.test/issues.json").mock(
        return_value=httpx.Response(
            200,
            json={"issues": [{"id": 1, "subject": "테스트", "description": "내용", "project": {"id": 1}}]},
        )
    )
    client = RedmineClient(base_url="http://redmine.test", api_key="testkey")
    issues = await client.get_issues(project_id=1)
    assert len(issues) == 1
    assert issues[0]["id"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_post_comment():
    respx.put("http://redmine.test/issues/1.json").mock(
        return_value=httpx.Response(200, json={})
    )
    client = RedmineClient(base_url="http://redmine.test", api_key="testkey")
    await client.post_comment(issue_id=1, comment="테스트 댓글")
    assert respx.calls.called
