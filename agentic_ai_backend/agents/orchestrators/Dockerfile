
FROM python:3.13-slim

WORKDIR /app

COPY agents/orchestrators/ ./agents/orchestrators/

WORKDIR /app/agents/orchestrators

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN uv sync --frozen

ENV PATH="/app/agents/orchestrators/.venv/bin:$PATH"

EXPOSE 8002
CMD ["python", "orchestrator_agent_server.py"]
