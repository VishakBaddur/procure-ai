# Combined Dockerfile: frontend + backend in one (for Render single Web Service)
# Build frontend, then run backend (which serves API + static frontend)

# ---- Frontend build (use Debian-based Node so Rollup native deps work on Linux) ----
FROM node:20-bookworm-slim AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
# Same-origin: backend will serve both API and static files, so use relative /api
ENV VITE_API_URL=
RUN npm run build

# ---- Backend + serve frontend ----
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY --from=frontend-build /app/dist ./frontend_dist

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
