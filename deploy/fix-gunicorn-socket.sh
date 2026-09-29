#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_SOURCE="$ROOT_DIR/deploy/reviewz.service"
SERVICE_DEST="/etc/systemd/system/reviewz.service"
SOCKET_PATH="/run/reviewz/gunicorn.sock"

if [[ "$EUID" -ne 0 ]]; then
    echo "Run this script as root: sudo $0" >&2
    exit 1
fi

echo "=== Step 1: Verify systemd service has SupplementaryGroups ==="
if ! grep -q '^SupplementaryGroups=reviewz-site$' "$SERVICE_SOURCE"; then
    echo "Adding SupplementaryGroups to $SERVICE_SOURCE..."
    sed -i '/^Group=www-data$/a SupplementaryGroups=reviewz-site' "$SERVICE_SOURCE"
fi

echo "=== Step 2: Install systemd service unit ==="
install -o root -g root -m 0644 "$SERVICE_SOURCE" "$SERVICE_DEST"
echo "✓ Installed $SERVICE_DEST"

echo "=== Step 3: Reload systemd daemon ==="
systemctl daemon-reload
echo "✓ Systemd daemon reloaded"

echo "=== Step 4: Restart reviewz service ==="
systemctl restart reviewz.service
echo "✓ Service restarted"

echo "=== Step 5: Wait for socket creation ==="
sleep 2

echo "=== Step 6: Check service status ==="
systemctl --no-pager --full status reviewz.service || true

echo "=== Step 7: Recent service logs ==="
journalctl -u reviewz.service -n 60 --no-pager || true

echo "=== Step 8: Verify socket file exists ==="
if [[ -S "$SOCKET_PATH" ]]; then
    echo "✓ Socket exists: $(ls -lh $SOCKET_PATH)"
else
    echo "✗ ERROR: Socket file not found at $SOCKET_PATH" >&2
    echo "  Service may have failed to start. Check logs above." >&2
    exit 1
fi

echo "=== Step 9: Test curl through Unix socket ==="
if curl --fail --show-error --max-time 5 \
    --unix-socket "$SOCKET_PATH" \
    -H 'Host: reviewz.site' \
    -H 'X-Forwarded-Proto: https' \
    http://localhost/ >/dev/null 2>&1; then
    echo "✓ Gunicorn is responding through Unix socket"
else
    echo "✗ ERROR: Curl test failed" >&2
    echo "  Socket exists but Gunicorn may not be responding properly." >&2
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ All checks passed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update Nginx site config:"
echo "   sudo cp /var/www/reviewz/deploy/nginx/reviewz.site.conf /etc/nginx/sites-available/reviewz.site"
echo "   sudo nginx -t && sudo systemctl reload nginx"
echo ""
echo "2. Or run the full deployment:"
echo "   cd /var/www/reviewz && git pull --ff-only && sudo ./deploy/deploy.sh"
