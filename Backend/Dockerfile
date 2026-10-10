# Shared base: dependencies and app code
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first so this layer is cached across code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (secrets and local files are excluded by .dockerignore)
COPY . .

# Bake the embedding model into the image so containers start without a download
RUN python -c "from services.llm.embedder import EmbedderService; EmbedderService().warm_up()"

# Run as a non-root user
RUN useradd -m -u 1000 sambhaash && chown -R sambhaash:sambhaash /app
USER sambhaash

# Force unbuffered stdout/stderr logging
ENV PYTHONUNBUFFERED=1


# Background worker only (docker-compose "worker" service)
FROM base AS worker
CMD ["python", "run_worker.py"]


# API only (docker-compose "api" service overrides CMD for --reload)
FROM base AS api
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]


# Default stage (what Render builds): API and worker in one container
FROM base AS production
# Expose port (Render defaults to 10000 for web services, but will bind to PORT)
EXPOSE 10000
CMD ["sh", "-c", "python run_worker.py & uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
