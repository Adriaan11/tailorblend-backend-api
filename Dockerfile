# TailorBlend AI Consultant - Backend API Dockerfile
# Python FastAPI + OpenAI Agents SDK
# Optimized for production deployment (fly.io, Railway, Google Cloud Run, etc.)

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (minimal footprint)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for Docker layer caching)
COPY backend/requirements-api.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY tb_agents/ ./tb_agents/
COPY config/ ./config/
COPY spec/ ./spec/
COPY instruction_parser.py token_counter.py vector_store_registry.py ./

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Default port for local development (overridden by fly.toml PYTHON_API_PORT=8080)
ENV PYTHON_API_PORT=5000

# Expose ports for documentation
EXPOSE 5000 8080

# Health check configuration
# Uses PYTHON_API_PORT which is set by fly.toml (8080) or defaults to 5000 locally
# Start period: 180s (3 minutes) for full app initialization including async startup
HEALTHCHECK --interval=15s --timeout=10s --start-period=180s --retries=3 \
    CMD curl -fsS http://127.0.0.1:${PYTHON_API_PORT:-5000}/health || exit 1

# Run the FastAPI server
# Uses PYTHON_API_PORT from environment (fly.toml sets to 8080, local defaults to 5000)
# Single worker prevents race conditions during heavy initialization
CMD ["/bin/sh", "-lc", "uvicorn backend.api:app --host 0.0.0.0 --port ${PYTHON_API_PORT:-5000} --workers 1 --log-level info"]
