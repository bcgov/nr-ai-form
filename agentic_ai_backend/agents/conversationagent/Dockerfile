
FROM python:3.13-slim
WORKDIR /app
COPY tools/ ./tools/
COPY conversationagent/ ./conversationagent/
WORKDIR /app/conversationagent
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN uv sync
ENV PATH="/app/conversationagent/.venv/bin:$PATH"
EXPOSE 8000
CMD ["python", "conversation_agent_a2a_server.py"]
