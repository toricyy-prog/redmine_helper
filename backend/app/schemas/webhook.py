from pydantic import BaseModel
from typing import Optional


class RedmineIssue(BaseModel):
    id: int
    subject: str
    description: Optional[str] = ""
    project: dict  # {"id": 1, "name": "..."}


class RedmineWebhookPayload(BaseModel):
    action: str  # "opened", "created" 등
    issue: RedmineIssue
