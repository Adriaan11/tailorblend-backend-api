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

# Default port (can be overridden by PORT environment variable)
ENV PYTHON_API_PORT=5000
ENV ASPNETCORE_ENVIRONMENT=Production

# Expose port for documentation
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://127.0.0.1:${PYTHON_API_PORT:-5000}/api/health || exit 1

# Run the FastAPI server
CMD ["python", "-m", "backend.api"]
