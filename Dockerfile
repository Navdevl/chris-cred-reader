FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Create directories for mounted volumes
RUN mkdir -p /app/logs

# Set Python path
ENV PYTHONPATH=/app/src

# Set default credentials path (will be overridden by volume mount)
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Health check to ensure the application is running
HEALTHCHECK --interval=5m --timeout=30s --start-period=30s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('/app/service-account.json') else 1)"

# Default command
CMD ["python", "src/main.py"]