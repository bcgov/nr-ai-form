
FROM python:3.13-slim
WORKDIR /app
COPY tools/ ./tools/
COPY conversationagent/ ./conversationagent/
WORKDIR /app/conversationagent
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN uv sync
ENV PATH="/app/conversationagent/.venv/bin:$PATH"

# Diagnostic: Check if ai_function is available in agent_framework
RUN python -c "from agent_framework import ai_function; print('✓ ai_function import SUCCESS')" 2>&1 || \
    python -c "import agent_framework; print('Available exports:', dir(agent_framework))"

EXPOSE 8000
CMD ["python", "conversation_agent_a2a_server.py"]
