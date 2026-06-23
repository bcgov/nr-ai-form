
FROM python:3.13-slim
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY utils/ ./utils/
COPY agents/tools/ ./agents/tools/
COPY agents/conversationagent/ ./agents/conversationagent/
WORKDIR /app/agents/conversationagent
RUN uv sync
ENV PATH="/app/agents/conversationagent/.venv/bin:$PATH"
EXPOSE 8000
CMD ["python", "conversation_agent_a2a_server.py"]
