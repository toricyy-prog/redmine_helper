import asyncio
from datetime import datetime, timedelta

import httpx

from app.config import settings


class RedmineClient:
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = (base_url or settings.redmine_url).rstrip("/")
        self.api_key = api_key or settings.redmine_api_key
        self.headers = {"X-Redmine-API-Key": self.api_key, "Content-Type": "application/json"}

    async def get_issues(self, project_id: int) -> list[dict]:
        """지정 프로젝트의 최근 N일 이슈 목록 조회"""
        since = (datetime.utcnow() - timedelta(days=settings.issue_search_days)).strftime("%Y-%m-%d")
        params = {"project_id": project_id, "created_on": f">={since}", "limit": 100, "status_id": "*"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            for attempt in range(2):
                try:
                    r = await client.get(
                        f"{self.base_url}/issues.json", params=params, headers=self.headers
                    )
                    r.raise_for_status()
                    return r.json().get("issues", [])
                except (httpx.HTTPError, httpx.TimeoutException):
                    if attempt == 1:
                        raise
        return []

    async def get_recent_issues(self, since: datetime) -> list[dict]:
        """특정 시각 이후 생성된 모든 프로젝트의 이슈 목록 조회 (폴링용)"""
        since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
        params = {"created_on": f">={since_str}", "limit": 100, "status_id": "*"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            for attempt in range(2):
                try:
                    r = await client.get(
                        f"{self.base_url}/issues.json", params=params, headers=self.headers
                    )
                    r.raise_for_status()
                    return r.json().get("issues", [])
                except (httpx.HTTPError, httpx.TimeoutException):
                    if attempt == 1:
                        raise
        return []

    async def get_issue(self, issue_id: int) -> dict:
        """이슈 상세 (댓글 포함) 조회"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{self.base_url}/issues/{issue_id}.json",
                params={"include": "journals"},
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json().get("issue", {})

    async def post_comment(self, issue_id: int, comment: str) -> None:
        """이슈에 댓글 작성 (3회 재시도 + 지수 백오프)"""
        body = {"issue": {"notes": comment}}
        async with httpx.AsyncClient(timeout=10.0) as client:
            for attempt in range(3):
                try:
                    r = await client.put(
                        f"{self.base_url}/issues/{issue_id}.json", json=body, headers=self.headers
                    )
                    r.raise_for_status()
                    return
                except (httpx.HTTPError, httpx.TimeoutException):
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2 ** attempt)

    async def update_custom_field(
        self, issue_id: int, custom_field_id: int, value: str
    ) -> None:
        """이슈 커스텀 필드 업데이트"""
        body = {"issue": {"custom_fields": [{"id": custom_field_id, "value": value}]}}
        async with httpx.AsyncClient(timeout=10.0) as client:
            for attempt in range(2):
                try:
                    r = await client.put(
                        f"{self.base_url}/issues/{issue_id}.json", json=body, headers=self.headers
                    )
                    r.raise_for_status()
                    return
                except (httpx.HTTPError, httpx.TimeoutException):
                    if attempt == 1:
                        raise
