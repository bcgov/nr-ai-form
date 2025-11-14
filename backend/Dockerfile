FROM python:3.11-slim

# Install system dependencies including curl for healthcheck
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (dependency manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files first (for better Docker layer caching)
COPY pyproject.toml uv.lock ./

# Remove readme reference from pyproject.toml to avoid build issues
RUN sed -i '/^readme = /d' pyproject.toml

# Install dependencies only (not the package itself)
RUN uv sync --frozen --no-cache --no-install-project

# Copy all application code into a 'backend' subdirectory to match the import structure
# This maintains the module structure where imports use 'from backend.x import y'
COPY . ./backend/

# Set Python path so 'backend' module imports work correctly
ENV PYTHONPATH=/app

# Set environment variables for Azure App Service
ENV PORT=8000
ENV HOST=0.0.0.0

# Expose port 8000 for FastAPI
EXPOSE 8000

# Health check endpoint for Azure App Service
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1

# Run the FastAPI app using uv run (ensures virtual environment is activated)
CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]