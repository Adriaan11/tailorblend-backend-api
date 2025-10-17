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
COPY instruction_parser.py token_counter.py ./

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Default port for local development
ENV PYTHON_API_PORT=5000

# Expose 5000 for documentation (Railway uses $PORT at runtime, but this is for reference)
EXPOSE 5000

# Health check configuration
# CRITICAL: Use ${PORT:-5000} to check the actual port the app is listening on
# Railway sets PORT internally; if not set, fall back to 5000
# Start period: 180s (3 minutes) for full app initialization including async startup
HEALTHCHECK --interval=15s --timeout=10s --start-period=180s --retries=3 \
    CMD curl -fsS http://127.0.0.1:${PORT:-5000}/api/health || exit 1

# Run the FastAPI server using shell form to expand $PORT
# This ensures uvicorn directly binds to 0.0.0.0:$PORT (Railway requirement)
# Railway provides $PORT; local dev uses fallback 5000
CMD ["/bin/sh", "-lc", "uvicorn backend.api:app --host 0.0.0.0 --port ${PORT:-5000} --workers 4"]
