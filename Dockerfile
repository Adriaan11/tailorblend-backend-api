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

# Default ports
# PYTHON_API_PORT is for local development (default 5000)
# PORT is set by Railway/containers and MUST be used for health checks
ENV PYTHON_API_PORT=5000
ENV ASPNETCORE_ENVIRONMENT=Production

# Expose port for documentation (8080 for Railway compatibility, but PORT is used at runtime)
EXPOSE 8000

# Health check configuration
# CRITICAL: Use ${PORT:-5000} to check the actual port the app is listening on
# Railway sets PORT internally; if not set, fall back to 5000
# Give 90 seconds for app to start (MultiAgentOrchestrator initialization takes time)
HEALTHCHECK --interval=15s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT:-5000}/api/health || exit 1

# Run the FastAPI server
# The app will listen on PORT if set (Railway), otherwise PYTHON_API_PORT (local)
CMD ["python", "-m", "backend.api"]
