# 스테이지 1: 프론트엔드 빌드
FROM node:20-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
# 빌드 결과: /frontend/../backend/static → /backend/static

# 스테이지 2: 백엔드
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
# 프론트엔드 빌드 결과물 복사
COPY --from=frontend-builder /backend/static ./static
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
