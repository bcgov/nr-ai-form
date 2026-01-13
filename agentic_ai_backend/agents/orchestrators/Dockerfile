
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY agents/orchestrators/ ./agents/orchestrators/

WORKDIR /app/agents/orchestrators

RUN uv sync

ENV PATH="/app/agents/orchestrators/.venv/bin:$PATH"

EXPOSE 8002
CMD ["python", "orchestrator_agent_server.py"]
