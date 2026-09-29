#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${1:-$ROOT_DIR/backups}"

if [[ "$EUID" -ne 0 ]]; then
    echo "Run the backup as root: sudo $ROOT_DIR/deploy/backup-db.sh [directory]" >&2
    exit 1
fi
mkdir -p "$BACKUP_DIR"
backup_file="$BACKUP_DIR/reviewz-$(date -u +%Y%m%dT%H%M%SZ)-$$.dump"
temporary_file="$backup_file.tmp"
trap 'rm -f -- "$temporary_file"' EXIT

runuser -u postgres -- pg_dump -Fc -d reviewz_site > "$temporary_file"
mv -- "$temporary_file" "$backup_file"
echo "Database backup written to $backup_file"
