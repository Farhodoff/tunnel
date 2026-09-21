# Tunnel Server Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY tunnel/ ./tunnel/
COPY pytest.ini ./pytest.ini

# Create non-root user + certs dir
RUN useradd -m -u 1000 tunnel && mkdir -p /app/certs && chown -R tunnel:tunnel /app
USER tunnel

# Expose ports
EXPOSE 8080

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV TUNNEL_DOMAIN=tunnel.dev
ENV TUNNEL_HOST=0.0.0.0
ENV TUNNEL_PORT=8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:${TUNNEL_PORT:-8080}/health || exit 1

# Run server (host/port/domain taken from env, overridable via CMD args)
CMD ["python", "-m", "tunnel.cli", "server"]
