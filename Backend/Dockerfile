# Multi-stage build for optimization
FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Production stage
FROM base as production

# Create non-root user for security
RUN useradd -m -u 1000 sambhaash && chown -R sambhaash:sambhaash /app
USER sambhaash

# Expose ports
# 8000 for API
EXPOSE 8000

# Default: Run FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Worker stage (for background job processing)
FROM base as worker

# Create non-root user
RUN useradd -m -u 1000 sambhaash && chown -R sambhaash:sambhaash /app
USER sambhaash

# Run background worker
CMD ["python", "run_worker.py"]
