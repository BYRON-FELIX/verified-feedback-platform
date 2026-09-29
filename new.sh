#!/usr/bin/env bash
set -Eeuo pipefail

INSTALL_DIR="/var/www/reviewz"
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$EUID" -ne 0 ]]; then
    echo "Please run this script with sudo or as root: sudo ./new.sh" >&2
    exit 1
fi

echo "=========================================================="
echo "⚠️  WARNING: COMPLETE RESET & FRESH RE-DEPLOYMENT"
echo "This will destroy the PostgreSQL database (reviewz_site),"
echo "remove existing Gunicorn/Nginx configs, clear .env, and"
echo "rebuild everything from scratch."
echo "=========================================================="
read -r -p "Are you sure you want to proceed? [y/N]: " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo ">>> [1/7] Stopping and removing Gunicorn systemd service..."
systemctl stop reviewz.service || true
systemctl disable reviewz.service || true
rm -f /etc/systemd/system/reviewz.service
systemctl daemon-reload
systemctl reset-failed

echo ">>> [2/7] Cleaning up sockets and runtime directories..."
rm -rf /run/reviewz
rm -f "$INSTALL_DIR/reviewz.sock" "$INSTALL_DIR/gunicorn.sock"

echo ">>> [3/7] Removing Reviewz Nginx site configuration..."
rm -f /etc/nginx/sites-enabled/reviewz.site
rm -f /etc/nginx/sites-available/reviewz.site
nginx -t && systemctl reload nginx

echo ">>> [4/7] Dropping PostgreSQL database and role..."
runuser -u postgres -- psql -v ON_ERROR_STOP=1 <<'SQL'
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'reviewz_site' AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS reviewz_site;
DROP ROLE IF EXISTS reviewz_site_app;
SQL

echo ">>> [5/7] Removing old virtualenv, staticfiles, and .env files..."
cd "$INSTALL_DIR"
rm -rf .venv staticfiles
rm -f .env .env.production

echo ">>> [6/7] Running fresh setup-vps.sh..."
"$INSTALL_DIR/deploy/setup-vps.sh"

echo ">>> [7/7] Installing Nginx configuration..."
cp "$INSTALL_DIR/deploy/nginx/reviewz.site.conf" /etc/nginx/sites-available/reviewz.site
ln -sf /etc/nginx/sites-available/reviewz.site /etc/nginx/sites-enabled/reviewz.site
nginx -t
systemctl reload nginx

echo ""
echo "=========================================================="
echo "✅ Fresh deployment completed successfully!"
echo "=========================================================="
echo ""
echo "Status check:"
systemctl --no-pager status reviewz.service || true

echo ""
echo "To issue SSL with Certbot, run:"
echo "  sudo certbot --nginx -d reviewz.site -d www.reviewz.site"
echo ""
echo "To create a Django superuser, run:"
echo "  sudo -u reviewz-site $INSTALL_DIR/.venv/bin/python \\"
echo "    $INSTALL_DIR/deploy/with-env.py $INSTALL_DIR/.env \\"
echo "    $INSTALL_DIR/.venv/bin/python $INSTALL_DIR/manage.py createsuperuser"
echo ""
echo "To load the review tasks fixture, run:"
echo "  sudo -u reviewz-site $INSTALL_DIR/.venv/bin/python \\"
echo "    $INSTALL_DIR/deploy/with-env.py $INSTALL_DIR/.env \\"
echo "    $INSTALL_DIR/.venv/bin/python $INSTALL_DIR/manage.py add_review_tasks --force"
echo ""
