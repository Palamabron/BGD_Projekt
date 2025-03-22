#!/bin/bash
# setup_pipeline.sh - Skrypt do sprawdzania endpointów i konfiguracji konektorów Debezium

# Ustawienia endpointów
DEBEZIUM_URL="http://localhost:8083/connectors"
MINIO_CONTAINER="minio"
MINIO_HEALTH_URL_LIVE="http://127.0.0.1:9000/minio/health/live"
MINIO_CLUSTER_URL="http://localhost:9000/minio/health/cluster"
ZOOKEEPER_HOST="localhost"
ZOOKEEPER_PORT="2181"

# Wait for all services to be fully ready
echo "Waiting for services to be fully ready..."
sleep 60

# Funkcja sprawdzająca dostępność endpointu z hosta (dla innych usług)
check_endpoint() {
  local name=$1
  local url=$2
  local max_attempts=10  # Increased from 5 to 10
  local attempt=1
  echo "Sprawdzam dostępność ${name} na ${url}..."
  while [ $attempt -le $max_attempts ]; do
    code=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    if [ "$code" == "200" ]; then
      echo "  ${name} jest dostępny (HTTP $code)."
      return 0
    else
      echo "  ${name} nie odpowiada (HTTP $code). Próba ${attempt}/${max_attempts}..."
      attempt=$((attempt+1))
      sleep 10  # Increased from 5 to 10 seconds
    fi
  done
  return 1
}

# Check container status
echo "Checking container status..."
docker ps | grep debezium

# Funkcja sprawdzająca dostępność MinIO z poziomu wnętrza kontenera
check_minio_inside_container() {
  local max_attempts=10  # Increased
  local attempt=1
  echo "Sprawdzam dostępność MinIO (wewnątrz kontenera) na ${MINIO_HEALTH_URL_LIVE}..."
  while [ $attempt -le $max_attempts ]; do
    code=$(docker exec ${MINIO_CONTAINER} curl -s -o /dev/null -w "%{http_code}" "$MINIO_HEALTH_URL_LIVE")
    if [ "$code" == "200" ]; then
      echo "  MinIO jest dostępny (HTTP $code)."
      return 0
    else
      echo "  MinIO nie odpowiada (HTTP $code). Próba ${attempt}/${max_attempts}..."
      attempt=$((attempt+1))
      sleep 10  # Increased
    fi
  done
  return 1
}

# Check Debezium logs for any errors
echo "Checking Debezium logs..."
docker logs debezium | tail -20

# Sprawdzenie dostępności Debezium Connect z hosta
if ! check_endpoint "Debezium Connect" "$DEBEZIUM_URL"; then
  echo "Debezium Connect niedostępny, przerywam."
  exit 1
fi

# Sprawdzenie dostępności MinIO – najpierw wewnątrz kontenera
if ! check_minio_inside_container; then
  echo "MinIO (node liveness) niedostępny, przerywam."
  exit 1
fi

# Sprawdzenie dostępności Zookeepera – jeśli jest mapowany na hosta
if nc -z -w5 $ZOOKEEPER_HOST $ZOOKEEPER_PORT; then
  echo "Zookeeper ($ZOOKEEPER_HOST:$ZOOKEEPER_PORT) jest dostępny."
else
  echo "Zookeeper ($ZOOKEEPER_HOST:$ZOOKEEPER_PORT) nie odpowiada. Upewnij się, że jest poprawnie skonfigurowany."
fi

echo "Konfiguracja konektorów Debezium..."

# Funkcja konfigurująca konektor Debezium
configure_connector() {
  local connector_name=$1
  local table_name=$2
  local slot_name=$3
  
  echo "Tworzenie konektora ${connector_name} dla tabeli ${table_name}..."
  response=$(curl -s -X POST -H "Content-Type: application/json" --data "{
    \"name\": \"${connector_name}\",
    \"config\": {
      \"connector.class\": \"io.debezium.connector.postgresql.PostgresConnector\",
      \"database.hostname\": \"postgres_db\",
      \"database.port\": \"5432\",
      \"database.user\": \"postgres\",
      \"database.password\": \"password\",
      \"database.dbname\": \"postgres\",
      \"database.server.name\": \"dbserver1\",
      \"table.include.list\": \"public.${table_name}\",
      \"plugin.name\": \"pgoutput\",
      \"topic.prefix\": \"dbserver1\",
      \"slot.name\": \"${slot_name}\",
      \"key.converter\": \"org.apache.kafka.connect.json.JsonConverter\",
      \"key.converter.schemas.enable\": \"false\",
      \"value.converter\": \"org.apache.kafka.connect.json.JsonConverter\",
      \"value.converter.schemas.enable\": \"false\",
      \"snapshot.mode\": \"initial\"
    }
  }" "$DEBEZIUM_URL")
  echo "$response" 
  echo ""
}

# Konfiguracja konektorów dla trzech tabel
configure_connector "klienci-connector" "klienci" "debezium_klienci"
sleep 5
configure_connector "pracownicy-connector" "pracownicy" "debezium_pracownicy"
sleep 5
configure_connector "projekty-connector" "projekty" "debezium_projekty"

echo "Konfiguracja konektorów zakończona."
echo "Sprawdzam status konektorów..."
curl -s "$DEBEZIUM_URL" 

echo "Skrypt zakończył działanie."