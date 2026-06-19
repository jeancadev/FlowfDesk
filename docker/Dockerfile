# Dockerfile — Multi-stage build for FlowDesk API
# Stage 1: Base with Python
FROM python:3.11-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Stage 2: Builder — install dependencies
FROM base AS builder
COPY pyproject.toml .
RUN pip install --no-cache-dir build && \
    pip install --no-cache-dir -e "."

# Stage 3: Production
FROM base AS production
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY app/ ./app/
COPY alembic.ini .

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run with gunicorn
CMD ["gunicorn", "app.main:create_app()", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
