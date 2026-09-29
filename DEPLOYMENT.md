# VPS deployment (Gunicorn and PostgreSQL)

This deployment runs Django under Gunicorn managed by systemd, with the
existing VPS PostgreSQL service and Nginx. It does not use Docker, install or
configure a PostgreSQL server, change firewall rules, or replace other sites.
The application listens only on `127.0.0.1:18081`; PostgreSQL database
`reviewz_site` and role `reviewz_site_app` are dedicated to this app.

## VPS prerequisites

Use an Ubuntu/Debian VPS with Python 3, `python3-venv`, PostgreSQL running
locally, Nginx, Certbot's Nginx plugin, Git, `sudo`, and `curl`. Install missing
packages using your OS's package manager, without removing or reconfiguring
packages used by other projects. Make sure Nginx and PostgreSQL are already
serving their existing projects normally.

The setup script refuses to change existing PostgreSQL roles or databases
named `reviewz_site_app` or `reviewz_site`; resolve any name conflict before
running it.

## Initial deployment

1. Point DNS `A` records for `reviewz.site` and `www.reviewz.site` to the VPS
   IPv4 address. Add `AAAA` records only if the server accepts IPv6 traffic.
2. Clone this repository to `/var/www/reviewz` and run:

   ```sh
   cd /var/www/reviewz
   sudo ./deploy/setup-vps.sh
   ```

   The script creates a restricted Linux service account, generates
   `.env.production` with restricted permissions and unique secrets, provisions
   the app-specific PostgreSQL role/database, creates the virtualenv, installs
   `requirements.txt`, runs migrations and `collectstatic`, and enables and
   starts the `reviewz` systemd service. The environment file is restricted
   to root and the app's service group.
3. Install this app's Nginx site alongside existing sites:

   ```sh
   sudo cp /var/www/reviewz/deploy/nginx/reviewz.site.conf /etc/nginx/sites-available/reviewz.site
   sudo ln -s /etc/nginx/sites-available/reviewz.site /etc/nginx/sites-enabled/reviewz.site
   sudo nginx -t
   sudo systemctl reload nginx
   ```

   If the symlink already exists, do not create a duplicate; check it points to
   this site config.
4. After both DNS names resolve to this VPS and port 80 is reachable, enable
   HTTPS for these domains:

   ```sh
   sudo certbot --nginx -d reviewz.site -d www.reviewz.site
   ```

   Keep `X-Forwarded-Proto` in the proxied Nginx location; Django relies on it
   behind TLS termination.
5. Configure PayHero credentials in `/var/www/reviewz/.env.production` if
   payments are enabled, then redeploy with `sudo ./deploy/deploy.sh`. Set
   PayHero's callback URL to
   `https://reviewz.site/payments/payhero/callback/`.
6. Create an admin account:

   ```sh
   sudo -u reviewz-site /var/www/reviewz/.venv/bin/python \
     /var/www/reviewz/deploy/with-env.py /var/www/reviewz/.env.production \
     /var/www/reviewz/.venv/bin/python /var/www/reviewz/manage.py createsuperuser
   ```

## Updates, logs, and backups

From `/var/www/reviewz`, update the checked-out code to the intended revision and
run `sudo ./deploy/deploy.sh`. This updates this app's virtualenv, database
migrations, static files, and systemd service; it does not restart other
projects.

View application logs with `sudo journalctl -u reviewz -f`. PostgreSQL backups
can be created with `sudo /var/www/reviewz/deploy/backup-db.sh
[/path/to/backup-directory]`. Copy backups off the VPS and verify a restore
before depending on them. User-uploaded media is in `/var/www/reviewz/media/` and
needs its own backup plan.
