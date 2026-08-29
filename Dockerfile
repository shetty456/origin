# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements /app/requirements

# BuildKit cache mount — pip packages are cached on the host between builds.
# Adding a new package only downloads that package, not everything.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements/dev.txt

COPY backend /app/backend

WORKDIR /app/backend

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
