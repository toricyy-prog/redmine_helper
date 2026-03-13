import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import settings


class SimilarityService:
    def __init__(
        self,
        threshold: float = None,
        duplicate_threshold: float = None,
        max_results: int = None,
    ):
        self.threshold = threshold if threshold is not None else settings.similarity_threshold
        self.duplicate_threshold = (
            duplicate_threshold if duplicate_threshold is not None else settings.duplicate_threshold
        )
        self.max_results = max_results if max_results is not None else settings.max_similar_issues

    def _to_text(self, issue: dict) -> str:
        """이슈 제목 + 설명을 하나의 텍스트로 합침"""
        subject = issue.get("subject", "")
        description = issue.get("description", "") or ""
        return f"{subject} {description}".strip()

    def find_similar(self, new_issue: dict, existing_issues: list[dict]) -> list[dict]:
        """
        새 이슈와 기존 이슈 목록 간 유사도 계산 후 상위 N개 반환.
        반환 형식: [{"id": int, "subject": str, "score": float, "is_duplicate": bool}]
        """
        if not existing_issues:
            return []

        new_text = self._to_text(new_issue)
        existing_texts = [self._to_text(issue) for issue in existing_issues]
        corpus = [new_text] + existing_texts

        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3))
        try:
            tfidf_matrix = vectorizer.fit_transform(corpus)
        except ValueError:
            return []

        new_vec = tfidf_matrix[0]
        existing_vecs = tfidf_matrix[1:]
        scores = cosine_similarity(new_vec, existing_vecs).flatten()

        results = []
        for idx, score in enumerate(scores):
            if score >= self.threshold:
                issue = existing_issues[idx]
                results.append(
                    {
                        "id": issue["id"],
                        "subject": issue.get("subject", ""),
                        "score": float(score),
                        "is_duplicate": bool(score >= self.duplicate_threshold),
                    }
                )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[: self.max_results]
