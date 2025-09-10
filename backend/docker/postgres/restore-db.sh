#!/bin/bash

# Database restore script for SMMS PostgreSQL
# Usage: ./restore-db.sh backup_file.sql

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file.sql>"
    echo "Available backups:"
    ls -la ./docker/postgres/backups/*.sql 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE=$1
CONTAINER_NAME="smms_postgres_dev"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file '$BACKUP_FILE' not found"
    exit 1
fi

echo "WARNING: This will replace all data in the database!"
read -p "Are you sure you want to restore from $BACKUP_FILE? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Restoring database from: $BACKUP_FILE"
    
    # Copy backup file to container and restore
    docker cp "$BACKUP_FILE" "$CONTAINER_NAME:/tmp/restore.sql"
    docker exec $CONTAINER_NAME psql -U postgres -d social-media-db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    docker exec $CONTAINER_NAME psql -U postgres -d social-media-db -f /tmp/restore.sql
    docker exec $CONTAINER_NAME rm /tmp/restore.sql
    
    echo "Database restored successfully!"
else
    echo "Restore cancelled."
fi
