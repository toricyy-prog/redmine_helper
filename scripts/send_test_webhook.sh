#!/bin/bash
# E2E 테스트용 웹훅 전송 스크립트
# 사용법: ./scripts/send_test_webhook.sh [SECRET] [URL]

SECRET="${1:-your_webhook_secret}"
BASE_URL="${2:-http://localhost:8000}"

PAYLOAD='{"action":"opened","issue":{"id":999,"subject":"로그인 페이지 500 오류","description":"로그인 시 500 에러가 발생합니다.","project":{"id":1,"name":"테스트 프로젝트"}}}'

SIG=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')

echo "=== 웹훅 전송 ==="
echo "URL: $BASE_URL/webhook/redmine"
echo "Signature: $SIG"
echo ""

curl -s -X POST "$BASE_URL/webhook/redmine" \
  -H "Content-Type: application/json" \
  -H "X-Redmine-Token: $SIG" \
  -d "$PAYLOAD"

echo ""
echo ""
echo "=== 잘못된 토큰 테스트 ==="
curl -s -X POST "$BASE_URL/webhook/redmine" \
  -H "Content-Type: application/json" \
  -H "X-Redmine-Token: wrong_token" \
  -d "$PAYLOAD"
echo ""
