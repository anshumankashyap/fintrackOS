# Stage 1: Builder
FROM python:3.11-slim AS builder

# System build dependencies (for psycopg2-binary compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create isolated virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python deps first (layer-cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt


# Stage 2: Runtime
FROM python:3.11-slim AS runtime

# Runtime system deps (only libpq for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN groupadd --gid 1001 appgroup \
 && useradd  --uid 1001 --gid appgroup --no-create-home appuser

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# App directory
WORKDIR /app

# Copy project source
COPY --chown=appuser:appgroup . .

# Create log and static directories
RUN mkdir -p /app/logs /app/staticfiles \
 && chown -R appuser:appgroup /app/logs /app/staticfiles

# Switch to non-root user
USER appuser

# Collect static files (WhiteNoise serves them without a separate web server)
RUN DJANGO_SETTINGS_MODULE=finance_backend.settings.production \
    SECRET_KEY=placeholder \
    DATABASE_URL=postgres://x:x@x/x \
    python manage.py collectstatic --noinput

# Expose application port
EXPOSE 8000

# Health check — hits the schema endpoint (no auth required)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/schema/')" || exit 1

# Entrypoint: run migrations then start Gunicorn
COPY --chown=appuser:appgroup scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
