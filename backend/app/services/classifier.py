import json
import logging

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

CLASSIFIER_SYSTEM_PROMPT = """당신은 Redmine 이슈 분류 전문가입니다.
주어진 이슈를 제공된 카테고리 중 하나로 분류하고, 분류 신뢰도(0.0~1.0)를 반환합니다.
반드시 다음 JSON 형식으로만 응답하세요:
{"category": "카테고리명", "confidence": 0.85}"""


class Classifier:
    def __init__(
        self,
        api_key: str = None,
        categories: list[str] = None,
        threshold: float = None,
    ):
        self.api_key = api_key or settings.claude_api_key
        self.categories = categories or settings.categories
        self.threshold = threshold if threshold is not None else settings.classification_threshold
        self._timeout = 30.0

    async def classify(self, subject: str, description: str) -> dict | None:
        """
        이슈를 카테고리로 분류.

        Returns:
            {"category": str, "confidence": float} — 신뢰도 임계값 이상인 경우
            None — 임계값 미만이거나 API 오류인 경우
        """
        categories_str = ", ".join(self.categories)
        prompt = (
            f"이슈 제목: {subject}\n"
            f"이슈 설명: {description[:500]}\n\n"
            f"가능한 카테고리: {categories_str}\n"
            f"위 카테고리 중 가장 적합한 것을 선택하고 신뢰도를 0.0~1.0으로 평가해주세요."
        )

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        try:
            response = await client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=128,
                timeout=self._timeout,
                system=CLASSIFIER_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()

            result = json.loads(raw)
            category = result.get("category")
            confidence = float(result.get("confidence", 0.0))

            if category not in self.categories:
                logger.warning(f"[Classifier] 유효하지 않은 카테고리 반환: {category}")
                return None

            if confidence < self.threshold:
                logger.info(
                    f"[Classifier] 신뢰도 미달 (confidence={confidence:.2f} < "
                    f"threshold={self.threshold}), 분류 보류"
                )
                return None

            return {"category": category, "confidence": confidence}

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"[Classifier] 응답 파싱 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"[Classifier] API 호출 실패: {e}")
            return None
