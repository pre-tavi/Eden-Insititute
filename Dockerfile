# ==============================================================================
# Eden Training Institute and Therapy (EdenLMS) — Production Backend Dockerfile
# Hardened Python 3.13-slim container running as non-root user `edenuser`
# ==============================================================================
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    PORT=8000

WORKDIR /app

# Create non-root system user
RUN groupadd --system --gid 10001 edengroup && \
    useradd --system --uid 10001 --gid edengroup --home /app edenuser

# Install Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend application source
COPY backend /app/backend
WORKDIR /app/backend

# Collect static files for WhiteNoise using a build-time dummy key
RUN DJANGO_SECRET_KEY="build-time-collectstatic-dummy-key-not-used-at-runtime-0123456789" \
    DJANGO_DEBUG=False \
    python manage.py collectstatic --noinput

RUN chown -R edenuser:edengroup /app
USER edenuser

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed_catalog && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 60"]