from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, JSON, Text

from app.db.session import Base


class IssueCache(Base):
    """Redmine 이슈 상세 조회 결과 캐시 (TTL: 1시간)"""
    __tablename__ = "issue_cache"

    issue_id = Column(Integer, primary_key=True)
    subject = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    journals = Column(JSON, nullable=True)  # 댓글 목록
    cached_at = Column(DateTime, default=datetime.utcnow)
