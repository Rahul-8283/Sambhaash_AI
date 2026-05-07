FROM python:3.11-slim

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

# Create non-root user for security
RUN useradd -m -u 1000 sambhaash && chown -R sambhaash:sambhaash /app
USER sambhaash

# Force unbuffered stdout/stderr logging
ENV PYTHONUNBUFFERED=1

# Expose port (Render defaults to 10000 for web services, but will bind to PORT)
EXPOSE 10000

# Default: Start worker in background and uvicorn in foreground
CMD ["sh", "-c", "python run_worker.py & uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
