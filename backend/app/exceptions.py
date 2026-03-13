class RedmineHelperError(Exception):
    """기본 에러 클래스"""
    pass


class RedmineAPIError(RedmineHelperError):
    """Redmine API 호출 실패"""
    error_code = "REDMINE_API_ERROR"


class ClaudeAPIError(RedmineHelperError):
    """Claude API 호출 실패"""
    error_code = "CLAUDE_API_ERROR"


class NoSimilarIssuesError(RedmineHelperError):
    """유사 이슈 없음 (에러가 아닌 정상 상태)"""
    error_code = "NO_SIMILAR_ISSUES"


class WebhookValidationError(RedmineHelperError):
    """웹훅 검증 실패"""
    error_code = "WEBHOOK_VALIDATION_ERROR"
