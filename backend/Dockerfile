FROM python:3.11-slim-bookworm

# Install system dependencies for WeasyPrint (PDF generation)
# Based on WeasyPrint docs for Debian 12 (Bookworm)
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    libcairo2 \
    fonts-liberation \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create temporary directory for file processing
RUN mkdir -p /tmp/bookflow

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV TEMP_DIR=/tmp/bookflow

# Expose port (Railway uses dynamic PORT env var)
EXPOSE 8000

# Default PORT for local development
ENV PORT=8000

# Start command - uses shell form to expand $PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
