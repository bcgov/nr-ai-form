# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

WORKDIR /app

# Install build dependencies required by some Python packages (for example, base2048 via pyrit)
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential curl gcc g++ libffi-dev rustc cargo && \
    rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app

# Install app dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install .

# Ensure results folder exists for generated reports
RUN mkdir -p /app/results

EXPOSE 8000

CMD ["uvicorn", "src.red_team.web_app:app", "--host", "0.0.0.0", "--port", "8000"]
