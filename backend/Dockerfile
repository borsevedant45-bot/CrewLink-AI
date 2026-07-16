FROM python:3.14-slim

WORKDIR /app

# Copy everything first so pip install finds the backend package.
# IMPORTANT: order matters — editable install must see backend/ at install time
# or it creates an empty namespace package that shadows the real one.
COPY pyproject.toml alembic.ini ./
COPY alembic/ ./alembic/
COPY backend/ ./backend/
COPY scripts/ ./scripts/

RUN pip install --no-cache-dir -e ".[dev]"

EXPOSE 8000

CMD ["sh", "scripts/startup.sh"]
