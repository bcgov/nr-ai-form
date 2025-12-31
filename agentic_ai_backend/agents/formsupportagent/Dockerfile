
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY utils/ ./utils/
COPY agents/formsupportagent/ ./agents/formsupportagent/
WORKDIR /app/agents/formsupportagent
RUN uv sync
ENV PATH="/app/agents/formsupportagent/.venv/bin:$PATH"
EXPOSE 8001
CMD ["python", "formsupport_agent_a2a_server.py"]
