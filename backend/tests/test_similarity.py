from app.services.similarity import SimilarityService


def test_find_similar_issues_basic():
    """유사한 이슈가 상위로 반환되는지 확인"""
    service = SimilarityService(threshold=0.1)
    existing = [
        {"id": 1, "subject": "로그인 오류 발생", "description": "로그인 페이지에서 500 에러"},
        {"id": 2, "subject": "배포 파이프라인 실패", "description": "CI/CD 빌드 실패"},
        {"id": 3, "subject": "데이터베이스 연결 오류", "description": "DB 커넥션 타임아웃"},
    ]
    new_issue = {"id": 10, "subject": "로그인 실패 오류", "description": "로그인 시 에러 발생"}
    results = service.find_similar(new_issue, existing)
    assert len(results) > 0
    assert results[0]["id"] == 1  # 가장 유사한 이슈


def test_find_similar_issues_below_threshold():
    """임계값 이하는 반환되지 않음"""
    service = SimilarityService(threshold=0.9)
    existing = [{"id": 1, "subject": "완전히 다른 주제", "description": "관련 없는 내용"}]
    new_issue = {"id": 10, "subject": "로그인 오류", "description": "로그인 실패"}
    results = service.find_similar(new_issue, existing)
    assert len(results) == 0


def test_find_similar_max_results():
    """최대 5개까지만 반환"""
    service = SimilarityService(threshold=0.0, max_results=5)
    existing = [{"id": i, "subject": f"이슈 {i}", "description": "공통 내용 로그인 오류"} for i in range(10)]
    new_issue = {"id": 99, "subject": "이슈 관련", "description": "공통 내용"}
    results = service.find_similar(new_issue, existing)
    assert len(results) <= 5


def test_duplicate_detection():
    """유사도 90% 이상이면 중복 플래그"""
    service = SimilarityService(threshold=0.1, duplicate_threshold=0.9)
    existing = [
        {
            "id": 1,
            "subject": "로그인 오류 발생 500에러",
            "description": "로그인 페이지 500 에러 발생",
        }
    ]
    new_issue = {
        "id": 10,
        "subject": "로그인 오류 발생 500에러",
        "description": "로그인 페이지 500 에러 발생",
    }
    results = service.find_similar(new_issue, existing)
    assert results[0]["is_duplicate"] is True
