
FROM python:3.13-slim
WORKDIR /app
COPY tools/ ./tools/
COPY conversationagent/ ./conversationagent/
WORKDIR /app/conversationagent
RUN pip install --no-cache-dir uv
RUN uv sync
ENV PATH="/app/conversationagent/.venv/bin:$PATH"
EXPOSE 8000
CMD ["python", "conversation_agent_a2a_server.py"]
