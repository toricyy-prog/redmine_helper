from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class SimilarIssueItem(BaseModel):
    id: int
    subject: str
    score: float
    is_duplicate: bool


class AnalysisHistoryItem(BaseModel):
    id: int
    issue_id: int
    project_id: int
    status: str  # success | failed | no_similar
    similar_issues: Optional[List[SimilarIssueItem]] = None
    ai_summary: Optional[str] = None
    created_at: datetime
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class AnalysisListResponse(BaseModel):
    items: List[AnalysisHistoryItem]
    total: int
    page: int
    page_size: int


class DuplicateDetectionItem(BaseModel):
    id: int
    source_issue_id: int
    target_issue_id: int
    similarity_score: float
    created_at: datetime

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total_analyzed: int
    total_success: int
    total_failed: int
    total_no_similar: int
    total_duplicates: int
    success_rate: float
    today_analyzed: int
    today_duplicates: int


class RerunRequest(BaseModel):
    issue_id: int
    project_id: int


class RerunResponse(BaseModel):
    status: str
    message: str
    analysis_id: Optional[int] = None
