#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR=/var/www/reviewz
if [[ -f "$INSTALL_DIR/.env" ]]; then
    ENV_FILE="$INSTALL_DIR/.env"
elif [[ -f "$INSTALL_DIR/.env.production" ]]; then
    ENV_FILE="$INSTALL_DIR/.env.production"
else
    ENV_FILE="$INSTALL_DIR/.env"
fi

if [[ "$EUID" -ne 0 ]]; then
    echo "Run deployment as root: sudo $ROOT_DIR/deploy/deploy.sh" >&2
    exit 1
fi
if [[ "$ROOT_DIR" != "$INSTALL_DIR" ]]; then
    echo "Expected checkout at $INSTALL_DIR." >&2
    exit 1
fi
if [[ ! -f "$ENV_FILE" ]]; then
    echo "Missing environment file ($INSTALL_DIR/.env or $INSTALL_DIR/.env.production). Run deploy/setup-vps.sh first." >&2
    exit 1
fi
for command in python3 runuser systemctl nginx curl; do
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

install -o root -g root -m 0644 "$ROOT_DIR/deploy/reviewz.service" /etc/systemd/system/reviewz.service
systemctl daemon-reload

NGINX_SITE=/etc/nginx/sites-available/reviewz.site
if [[ -f "$NGINX_SITE" ]]; then
    python3 - "$NGINX_SITE" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
content = path.read_text()
old_proxies = (
    "proxy_pass http://127.0.0.1:18081;",
    "proxy_pass http://unix:/var/www/reviewz/reviewz.sock;",
    "proxy_pass http://unix:/var/www/reviewz/reviewz.sock:/;",
)
new_proxy = "proxy_pass http://unix:/run/reviewz/gunicorn.sock:/;"
old_count = sum(content.count(proxy) for proxy in old_proxies)

if new_proxy in content:
    if content.count(new_proxy) != 1 or old_count:
        raise SystemExit(f"Cannot safely update {path}: multiple Reviewz proxy directives found.")
else:
    matches = [proxy for proxy in old_proxies if content.count(proxy)]
    if len(matches) != 1 or old_count != 1:
        raise SystemExit(
            f"Cannot safely update {path}: expected exactly one known Reviewz proxy_pass directive."
        )
    path.write_text(content.replace(matches[0], new_proxy))
PY
    nginx -t
else
    echo "Nginx site $NGINX_SITE not found; install it using DEPLOYMENT.md." >&2
fi

systemctl restart reviewz.service
if [[ -f "$NGINX_SITE" ]]; then
    systemctl reload nginx
fi
systemctl --no-pager --full status reviewz.service
curl --fail --silent --show-error --max-time 5 \
    --unix-socket /run/reviewz/gunicorn.sock \
    -H 'Host: reviewz.site' \
    -H 'X-Forwarded-Proto: https' \
    http://localhost/ >/dev/null
echo "Reviewz deployment is healthy through /run/reviewz/gunicorn.sock."
