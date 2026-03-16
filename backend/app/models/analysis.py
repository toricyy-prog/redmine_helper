from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, Text

from app.db.session import Base


class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, nullable=False, index=True)
    project_id = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False)  # success | failed | no_similar | comment_skipped
    similar_issues = Column(JSON, nullable=True)
    ai_summary = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)       # Sprint 2 추가
    category_confidence = Column(Float, nullable=True)  # Sprint 2 추가
    comment_written = Column(Integer, default=0)        # Sprint 2 추가 (0/1)
    created_at = Column(DateTime, default=datetime.utcnow)
    error_message = Column(Text, nullable=True)


class DuplicateDetection(Base):
    __tablename__ = "duplicate_detections"

    id = Column(Integer, primary_key=True, index=True)
    source_issue_id = Column(Integer, nullable=False, index=True)
    target_issue_id = Column(Integer, nullable=False)
    similarity_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
