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

    class Config:
        env_file = ".env"


settings = Settings()
