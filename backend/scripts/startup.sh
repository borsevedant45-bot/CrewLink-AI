#!/usr/bin/env sh
# path: backend/scripts/startup.sh
# Startup script that handles the Alembic → seed → uvicorn bootstrap.
#
# alembic can return 0 before SQLite has fully committed DDL to disk.
# This script retries the seed step with backoff until tables are confirmed
# present, closing the race condition between migration and seed.

set -e

# Step 1: Apply pending migrations
echo ">>> Running Alembic migrations..."
alembic upgrade head
echo "<<< Alembic done."

# Step 2: Seed the database (retry loop for SQLite DDL propagation delay)
echo ">>> Seeding database..."
MAX_RETRIES=10
RETRY_DELAY=1
i=0
while [ $i -lt $MAX_RETRIES ]; do
  if python -c "
from backend.app.db.session import SessionLocal
from backend.app.seed.data import seed_all
from sqlalchemy import inspect
db = SessionLocal()
try:
    inspector = inspect(db.connection())
    tables = inspector.get_table_names()
    if 'incidents' in tables:
        seed_all(db)
        print('Seed complete.')
    else:
        print('Tables found: ' + str(tables) + ' — incidents not ready yet, retrying...')
        raise RuntimeError('incidents table not found')
except Exception:
    raise
finally:
    db.close()
"; then
    echo "<<< Seed done."
    break
  else
    i=$((i + 1))
    if [ $i -ge $MAX_RETRIES ]; then
      echo "ERROR: Seed failed after $MAX_RETRIES retries. Aborting."
      exit 1
    fi
    echo "Retrying in ${RETRY_DELAY}s... ($i/$MAX_RETRIES)"
    sleep $RETRY_DELAY
    RETRY_DELAY=$((RETRY_DELAY * 2))
    [ $RETRY_DELAY -gt 10 ] && RETRY_DELAY=10
  fi
done

# Step 3: Start the server
echo ">>> Starting uvicorn..."
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
