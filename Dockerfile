# Multi-stage build for Finance GraphRAG
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY data/ ./data/
COPY mcp-config.json .
COPY README.md .
COPY schema.md .

# Create data_sources.json (will be created/overwritten by volume mount if exists)
RUN echo '{"pdf": [], "text": [], "url": []}' > data_sources.json

# Create necessary directories
RUN mkdir -p logs storage/graph_storage

# Expose ports
# 8000: FastAPI backend
# 8501: Streamlit frontend
EXPOSE 8000 8501

# Default command (can be overridden in docker-compose)
CMD ["python", "src/app.py"]

