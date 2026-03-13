from sqlalchemy import Column, Float, Integer, String, Text

from app.db.session import Base


class AppSettings(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, default=1)
    similarity_threshold = Column(Float, default=0.3)
    duplicate_threshold = Column(Float, default=0.9)
    max_similar_issues = Column(Integer, default=5)
    category_list = Column(Text, default="")  # 쉼표 구분 카테고리 목록
    enable_auto_comment = Column(String(10), default="false")
