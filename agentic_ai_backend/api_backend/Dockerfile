FROM python:3.13-slim
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY utils/ ./utils/
COPY api_backend/ ./api_backend/
WORKDIR /app/api_backend
RUN uv sync
ENV PATH="/app/api_backend/.venv/bin:$PATH"
EXPOSE 8003
CMD ["python", "api_backend_server.py"]