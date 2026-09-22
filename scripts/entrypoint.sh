#!/usr/bin/env bash
set -e

# Wait for Postgres
if [ -n "$POSTGRES_HOST" ]; then
  echo "Waiting for postgres at ${POSTGRES_HOST}:${POSTGRES_PORT:-5432}..."
  while ! nc -z "${POSTGRES_HOST}" "${POSTGRES_PORT:-5432}"; do
    sleep 1
  done
  echo "Postgres is up."
fi

# Wait for Redis (best-effort)
if [ -n "$REDIS_URL" ]; then
  REDIS_HOST=$(echo "$REDIS_URL" | sed -E 's|redis://([^:/]+).*|\1|')
  REDIS_PORT=$(echo "$REDIS_URL" | sed -E 's|.*:([0-9]+)/.*|\1|')
  if [ -n "$REDIS_HOST" ] && [ -n "$REDIS_PORT" ]; then
    echo "Waiting for redis at ${REDIS_HOST}:${REDIS_PORT}..."
    while ! nc -z "${REDIS_HOST}" "${REDIS_PORT}"; do
      sleep 1
    done
    echo "Redis is up."
  fi
fi

exec "$@"