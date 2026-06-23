FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir uv && uv sync --no-dev
COPY src /app/src
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "marketing_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]

