# Tunnel Server Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY tunnel/ ./tunnel/

# Expose ports
EXPOSE 8080

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV TUNNEL_DOMAIN=tunnel.dev

# Run server
CMD ["python", "-m", "tunnel.cli", "server", "--host", "0.0.0.0", "--port", "8080"]
