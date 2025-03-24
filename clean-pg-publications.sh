#!/bin/bash
# Script to clean PostgreSQL publications and replication slots

# Colors for formatting
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Cleaning PostgreSQL Publications and Replication Slots ===${NC}"

# First check if PostgreSQL container is running
if ! docker ps | grep -q postgres_db; then
  echo -e "${RED}PostgreSQL container is not running!${NC}"
  exit 1
fi

# Drop publications
echo -e "${BLUE}Dropping PostgreSQL publications...${NC}"
docker exec postgres_db psql -U postgres -c "
DO \$\$
DECLARE
  pub_name text;
BEGIN
  FOR pub_name IN (SELECT pubname FROM pg_publication)
  LOOP
    EXECUTE 'DROP PUBLICATION IF EXISTS ' || pub_name || ' CASCADE;';
    RAISE NOTICE 'Dropped publication %', pub_name;
  END LOOP;
END;
\$\$;
"

# Drop replication slots
echo -e "${BLUE}Dropping PostgreSQL replication slots...${NC}"
docker exec postgres_db psql -U postgres -c "
DO \$\$
DECLARE
  slot_name text;
BEGIN
  FOR slot_name IN (SELECT slot_name FROM pg_replication_slots)
  LOOP
    EXECUTE 'SELECT pg_drop_replication_slot(''' || slot_name || ''');';
    RAISE NOTICE 'Dropped replication slot %', slot_name;
  END LOOP;
END;
\$\$;
"

echo -e "${GREEN}PostgreSQL publications and replication slots cleaned.${NC}"