#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR=/var/www/reviewz
ENV_FILE="$INSTALL_DIR/.env.production"

if [[ "$EUID" -ne 0 ]]; then
    echo "Run deployment as root: sudo $ROOT_DIR/deploy/deploy.sh" >&2
    exit 1
fi
if [[ "$ROOT_DIR" != "$INSTALL_DIR" ]]; then
    echo "Expected checkout at $INSTALL_DIR." >&2
    exit 1
fi
if [[ ! -f "$ENV_FILE" ]]; then
    echo "Missing $ENV_FILE. Run deploy/setup-vps.sh first." >&2
    exit 1
fi
for command in python3 runuser systemctl; do
    command -v "$command" >/dev/null 2>&1 || {
        printf 'Required command not found: %s\n' "$command" >&2
        exit 1
    }
done

chown root:reviewz-site "$ENV_FILE"
chmod 640 "$ENV_FILE"
install -d -o reviewz-site -g reviewz-site "$INSTALL_DIR/media" "$INSTALL_DIR/staticfiles"

if [[ ! -x "$INSTALL_DIR/.venv/bin/python" ]]; then
    runuser -u reviewz-site -- python3 -m venv "$INSTALL_DIR/.venv"
fi

chown -R reviewz-site:reviewz-site "$INSTALL_DIR/.venv"
runuser -u reviewz-site -- "$INSTALL_DIR/.venv/bin/pip" install --no-cache-dir --upgrade pip
runuser -u reviewz-site -- "$INSTALL_DIR/.venv/bin/pip" install --no-cache-dir -r "$ROOT_DIR/requirements.txt"
runuser -u reviewz-site -- "$INSTALL_DIR/.venv/bin/python" "$ROOT_DIR/deploy/with-env.py" \
    "$ENV_FILE" "$INSTALL_DIR/.venv/bin/python" "$ROOT_DIR/manage.py" migrate --noinput
runuser -u reviewz-site -- "$INSTALL_DIR/.venv/bin/python" "$ROOT_DIR/deploy/with-env.py" \
    "$ENV_FILE" "$INSTALL_DIR/.venv/bin/python" "$ROOT_DIR/manage.py" collectstatic --noinput

systemctl restart reviewz.service
systemctl --no-pager --full status reviewz.service
curl --fail --silent --show-error --max-time 5 \
    -H 'Host: reviewz.site' \
    -H 'X-Forwarded-Proto: https' \
    http://127.0.0.1:18081/ >/dev/null
echo "Reviewz deployment is healthy on 127.0.0.1:18081."
