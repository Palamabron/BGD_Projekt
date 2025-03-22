#!/bin/bash
# This script modifies PostgreSQL wal_level on a running container

# Check if container is running
if ! docker ps | grep -q postgres_db; then
  echo "PostgreSQL container is not running"
  exit 1
fi

echo "Modifying PostgreSQL wal_level setting..."

# Connect to PostgreSQL and check current wal_level
echo "Current wal_level setting:"
docker exec postgres_db psql -U postgres -c "SHOW wal_level;"

# Set wal_level to logical
echo "Setting wal_level to logical..."
docker exec postgres_db psql -U postgres -c "ALTER SYSTEM SET wal_level = logical;"

# Restart PostgreSQL to apply changes
echo "Restarting PostgreSQL inside the container..."
docker exec postgres_db pg_ctl -D /var/lib/postgresql/data -m fast restart

# Wait for PostgreSQL to restart
echo "Waiting for PostgreSQL to start up again..."
sleep 10

# Verify the new setting
echo "New wal_level setting:"
docker exec postgres_db psql -U postgres -c "SHOW wal_level;"

echo "PostgreSQL wal_level modification complete"