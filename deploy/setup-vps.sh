#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR=/var/www/reviewz
if [[ -f "$INSTALL_DIR/.env" ]]; then
    ENV_FILE="$INSTALL_DIR/.env"
elif [[ -f "$INSTALL_DIR/.env.production" ]]; then
    ENV_FILE="$INSTALL_DIR/.env.production"
else
    ENV_FILE="$INSTALL_DIR/.env"
fi
created_env=false

if [[ "$EUID" -ne 0 ]]; then
    echo "Run this setup script as root: sudo $ROOT_DIR/deploy/setup-vps.sh" >&2
    exit 1
fi
if [[ "$ROOT_DIR" != "$INSTALL_DIR" ]]; then
    echo "Clone the project to $INSTALL_DIR before running setup." >&2
    exit 1
fi
for command in python3 openssl runuser nginx systemctl; do
    command -v "$command" >/dev/null 2>&1 || {
        printf 'Required command not found: %s\n' "$command" >&2
        exit 1
    }
done
runuser -u postgres -- psql -v ON_ERROR_STOP=1 -c 'SELECT 1' >/dev/null

if [[ ! -f "$ENV_FILE" ]]; then
    existing_resources="$(runuser -u postgres -- psql -At -c "SELECT 'role' FROM pg_roles WHERE rolname = 'reviewz_site_app' UNION ALL SELECT 'database' FROM pg_database WHERE datname = 'reviewz_site'")"
    if [[ -n "$existing_resources" ]]; then
        echo "PostgreSQL resource name already in use ($existing_resources); refusing to change it." >&2
        exit 1
    fi
    cp "$ROOT_DIR/deploy/env.production.example" "$ENV_FILE"
    secret_key="$(openssl rand -hex 48)"
    database_password="$(openssl rand -hex 32)"
    sed -i \
        -e "s/^DJANGO_SECRET_KEY=GENERATE_ON_FIRST_SETUP$/DJANGO_SECRET_KEY=$secret_key/" \
        -e "s/^DATABASE_URL=postgresql:\/\/reviewz_site_app:GENERATE_ON_FIRST_SETUP@127.0.0.1:5432\/reviewz_site$/DATABASE_URL=postgresql:\/\/reviewz_site_app:$database_password@127.0.0.1:5432\/reviewz_site/" \
        "$ENV_FILE"
    created_env=true
fi

if ! id reviewz-site >/dev/null 2>&1; then
    useradd --system --home-dir "$INSTALL_DIR" --no-create-home \
        --shell /usr/sbin/nologin reviewz-site
fi

if [[ "$created_env" == true ]]; then
    echo "Created $ENV_FILE with generated application and database secrets."
fi

if grep -q 'GENERATE_ON_FIRST_SETUP' "$ENV_FILE"; then
    echo "Uninitialized secret placeholder found in $ENV_FILE." >&2
    exit 1
fi
chown root:reviewz-site "$ENV_FILE"
chmod 640 "$ENV_FILE"

install -d -o reviewz-site -g reviewz-site "$INSTALL_DIR/media" "$INSTALL_DIR/staticfiles"

database_password="$(sed -n 's|^DATABASE_URL=postgresql://reviewz_site_app:\([^@]*\)@127\.0\.0\.1:5432/reviewz_site$|\1|p' "$ENV_FILE")"
if [[ -z "$database_password" || ! "$database_password" =~ ^[a-fA-F0-9]+$ ]]; then
    echo "DATABASE_URL must use the local reviewz_site_app/reviewz_site database with a hex password." >&2
    exit 1
fi

runuser -u postgres -- psql -v ON_ERROR_STOP=1 \
    -v "app_password=$database_password" <<'SQL'
SELECT format('CREATE ROLE reviewz_site_app LOGIN PASSWORD %L', :'app_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'reviewz_site_app')
\gexec
ALTER ROLE reviewz_site_app WITH LOGIN PASSWORD :'app_password';
SELECT format('CREATE DATABASE reviewz_site OWNER reviewz_site_app')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'reviewz_site')
\gexec
DO $$
BEGIN
    IF (SELECT pg_catalog.pg_get_userbyid(datdba) FROM pg_database WHERE datname = 'reviewz_site') <> 'reviewz_site_app' THEN
        RAISE EXCEPTION 'Database reviewz_site already exists and is not owned by reviewz_site_app; refusing to change an existing database';
    END IF;
END
$$;
SQL

install -o root -g root -m 0644 "$ROOT_DIR/deploy/reviewz.service" /etc/systemd/system/reviewz.service
systemctl daemon-reload
systemctl enable reviewz.service

"$ROOT_DIR/deploy/deploy.sh"

echo "Install the Nginx site and TLS certificate as described in DEPLOYMENT.md."