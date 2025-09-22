# Backend Dockerfile (Django)
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install OS dependencies (timezone, curl) and clean up
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend project
COPY . /app

# Expose port
EXPOSE 8000

# Default environment variables (override in compose/prod)
ENV DEBUG=false \
    DJANGO_SETTINGS_MODULE=backend.settings \
    PYTHONPATH=/app

# Run migrations and start gunicorn
CMD ["bash", "-lc", "python manage.py collectstatic --noinput && python manage.py migrate && gunicorn backend.wsgi:application --bind 0.0.0.0:8000"]
