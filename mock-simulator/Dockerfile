FROM python:3.14-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY app/ app/

CMD ["python", "-m", "mock_simulator.app.main"]
