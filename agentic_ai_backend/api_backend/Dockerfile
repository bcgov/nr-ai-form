
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY utils/ ./utils/
COPY api_backend/ ./api_backend/
WORKDIR /app/api_backend
RUN uv sync
ENV PATH="/app/api_backend/.venv/bin:$PATH"
EXPOSE 8003
CMD ["python", "api_backend_server.py"]
