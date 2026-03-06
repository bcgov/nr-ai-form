
FROM python:3.13-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY utils/ ./utils/
COPY agents/orchestrators/ ./agents/orchestrators/

WORKDIR /app/agents/orchestrators

RUN uv sync

ENV PATH="/app/agents/orchestrators/.venv/bin:$PATH"

EXPOSE 8002
CMD ["python", "orchestrator_agent_server.py"]
