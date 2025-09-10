#!/bin/bash

# Database backup script for SMMS PostgreSQL
# Usage: ./backup-db.sh [backup_name]

set -e

BACKUP_NAME=${1:-"smms-backup-$(date +%Y%m%d_%H%M%S)"}
CONTAINER_NAME="smms_postgres_dev"

echo "Creating backup: $BACKUP_NAME"

# Create backup using docker exec
docker exec $CONTAINER_NAME pg_dump -U postgres social-media-db > "./docker/postgres/backups/${BACKUP_NAME}.sql"

echo "Backup created: ./docker/postgres/backups/${BACKUP_NAME}.sql"
echo "Backup size: $(du -h ./docker/postgres/backups/${BACKUP_NAME}.sql | cut -f1)"
