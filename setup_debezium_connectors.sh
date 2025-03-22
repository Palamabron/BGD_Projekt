#!/bin/bash
# Configure Debezium connectors for PostgreSQL tables

echo "Setting up Debezium connectors for PostgreSQL tables..."

# Wait for PostgreSQL to be fully ready
echo "Waiting for PostgreSQL to be ready..."
until docker exec postgres_db pg_isready -U postgres; do
  echo "PostgreSQL not ready yet, waiting..."
  sleep 2
done

# Ensure the tables exist in PostgreSQL
echo "Creating tables in PostgreSQL if they don't exist..."
docker exec postgres_db psql -U postgres -c "
CREATE TABLE IF NOT EXISTS klienci (
  id SERIAL PRIMARY KEY,
  nazwa VARCHAR(100),
  email VARCHAR(100),
  kraj VARCHAR(50),
  telefon VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS pracownicy (
  id SERIAL PRIMARY KEY,
  imie VARCHAR(50),
  nazwisko VARCHAR(50),
  email VARCHAR(100),
  wiek INTEGER,
  stanowisko VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS projekty (
  id SERIAL PRIMARY KEY,
  nazwa VARCHAR(100),
  opis TEXT,
  data_rozpoczecia DATE,
  data_zakonczenia DATE
);"

# Function to configure Debezium connectors
create_connector() {
  local connector_name=$1
  local table_name=$2
  local slot_name=$3

  echo "Creating connector: ${connector_name} for table: ${table_name}..."
  
  curl -X POST \
    -H "Content-Type: application/json" \
    -d '{
      "name": "'"${connector_name}"'",
      "config": {
        "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
        "database.hostname": "postgres_db",
        "database.port": "5432",
        "database.user": "postgres",
        "database.password": "password",
        "database.dbname": "postgres",
        "database.server.name": "dbserver1",
        "table.include.list": "public.'"${table_name}"'",
        "plugin.name": "pgoutput",
        "topic.prefix": "dbserver1",
        "slot.name": "'"${slot_name}"'",
        "key.converter": "org.apache.kafka.connect.json.JsonConverter",
        "key.converter.schemas.enable": "false",
        "value.converter": "org.apache.kafka.connect.json.JsonConverter",
        "value.converter.schemas.enable": "false",
        "snapshot.mode": "initial"
      }
    }' \
    http://localhost:8083/connectors
    
  echo ""
}

# Create connectors for the three tables
create_connector "klienci-connector" "klienci" "debezium_klienci"
sleep 3
create_connector "pracownicy-connector" "pracownicy" "debezium_pracownicy"
sleep 3
create_connector "projekty-connector" "projekty" "debezium_projekty"

# Verify connector status
echo "Checking connector status..."
curl -s http://localhost:8083/connectors | jq .

echo "Setup complete!"