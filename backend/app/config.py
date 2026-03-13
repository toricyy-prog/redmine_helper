from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redmine_url: str = "http://localhost"
    redmine_api_key: str = ""
    claude_api_key: str = ""
    webhook_secret: str = "test_secret"
    dashboard_password: str = "password"
    issue_detection_mode: str = "webhook"
    # 운영 안전 플래그: True로 설정해야 Redmine에 댓글이 자동 작성됨 (기본 비활성화)
    enable_auto_comment: bool = False
    similarity_threshold: float = 0.3
    duplicate_threshold: float = 0.9
    max_similar_issues: int = 5
    issue_search_days: int = 365
    database_url: str = "sqlite:////data/redmine_helper.db"
    # Sprint 2 추가
    category_list: str = "버그,기능요청,문의,성능,보안"
    classification_threshold: float = 0.7
    redmine_category_field_id: str = ""
    # Sprint 3 추가 — JWT 인증
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24시간

    @property
    def categories(self) -> List[str]:
        return [c.strip() for c in self.category_list.split(",") if c.strip()]

    class Config:
        env_file = ("../.env", ".env")  # 루트 또는 backend/ 디렉토리 모두 탐색


settings = Settings()
