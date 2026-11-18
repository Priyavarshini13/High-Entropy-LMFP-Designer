# ==============================================================================
# ECMT AI — Production Dockerfile for Railway Cloud Deployment
# Packages: React 19 Frontend + FastAPI Backend + ML Models + SQLite Database
# ==============================================================================

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application directories
COPY backend/ backend/
COPY chemistry/ chemistry/
COPY copilot/ copilot/
COPY experiments/ experiments/
COPY literature/ literature/
COPY models/ models/
COPY data/ data/

# Copy pre-compiled React distribution
COPY frontend/dist/ frontend/dist/

# Create persistent storage directories for uploads and SQLite
RUN mkdir -p data/uploads/images data/uploads/experiments data/uploads/literature

# Declare mount points for Railway Persistent Volume
VOLUME ["/app/data/uploads", "/app/data"]

EXPOSE 8000

# Start production server
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
