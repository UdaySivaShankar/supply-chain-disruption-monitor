#!/usr/bin/env sh
# Runs the verification suite required before delivery:
#   backend tests, frontend build, database migrations, seed data,
#   docker compose validation.
#
# Usage:  sh scripts/verify.sh

set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)

echo "1/5 Backend test suite"
cd "$ROOT/backend"
python -m pytest tests -q

echo "2/5 Frontend production build"
cd "$ROOT/frontend"
npm run build

echo "3/5 Database migrations on a clean database"
cd "$ROOT/backend"
rm -f verify_migrations.db
DATABASE_URL="sqlite:///verify_migrations.db" alembic upgrade head

echo "4/5 Seed demo data"
DATABASE_URL="sqlite:///verify_migrations.db" python scripts/seed_data.py
rm -f verify_migrations.db

echo "5/5 Docker Compose configuration"
cd "$ROOT"
if command -v docker >/dev/null 2>&1; then
  docker compose config --quiet
  echo "Compose file valid. Start the stack with: docker compose up -d"
else
  echo "Docker is not installed. Validating compose files directly."
  "$ROOT/backend/.venv/bin/python" "$ROOT/scripts/validate_compose.py" \
    || python3 "$ROOT/scripts/validate_compose.py"
fi

echo "Verification finished successfully."
