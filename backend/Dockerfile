# Backend Dockerfile for Procurement AI
FROM python:3.12-slim

# Install system deps for PDF/OCR (optional; omit if you don't need pytesseract)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render and many PaaS set PORT; default 8000 for local/Docker
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
