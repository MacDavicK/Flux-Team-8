FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer)
# ============================================================
# Flux DAO Service — Dockerfile
# Internal microservice: not exposed outside the Docker network.
# Other Flux services (Goal Planner, Scheduler, Observer) access
# this service over the internal flux-internal network.
# ============================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for asyncpg (PostgreSQL client libs)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install production dependencies only
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
COPY dao_service/ dao_service/

# Expose the service port
EXPOSE 8000

# Health check — polls the /health endpoint every 30 seconds
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run uvicorn with production settings
CMD ["uvicorn", "dao_service.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
