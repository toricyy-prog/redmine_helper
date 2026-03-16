from typing import List, Optional

from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    similarity_threshold: float
    duplicate_threshold: float
    max_similar_issues: int
    category_list: List[str]
    enable_auto_comment: bool


class SettingsUpdateRequest(BaseModel):
    similarity_threshold: Optional[float] = Field(None, ge=0.1, le=1.0)
    duplicate_threshold: Optional[float] = Field(None, ge=0.1, le=1.0)
    max_similar_issues: Optional[int] = Field(None, ge=1, le=20)
    category_list: Optional[List[str]] = None
    enable_auto_comment: Optional[bool] = None
