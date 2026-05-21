FROM python:3.13-slim

RUN pip install --no-cache-dir uv

WORKDIR /app/api

COPY api/ ./

RUN uv sync

ENV PATH="/app/api/.venv/bin:$PATH"

EXPOSE 8080

CMD ["python", "main.py"]
