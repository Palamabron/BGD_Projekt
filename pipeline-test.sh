#!/bin/bash
# Pipeline test script for troubleshooting

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}===== Data Pipeline Test Script =====${NC}"
echo "Running tests to verify each component is working correctly..."

# Function to check if a container is running
check_container() {
  container_name=$1
  echo -n "Checking if $container_name is running... "
  
  if [ "$(docker ps -q -f name=$container_name)" ]; then
    echo -e "${GREEN}OK${NC}"
    return 0
  else
    echo -e "${RED}NOT RUNNING${NC}"
    return 1
  fi
}

# Function to check if a service port is accessible
check_port() {
  service_name=$1
  host=$2
  port=$3
  
  echo -n "Checking if $service_name is accessible on $host:$port... "
  
  if nc -z -w 5 $host $port; then
    echo -e "${GREEN}OK${NC}"
    return 0
  else
    echo -e "${RED}FAILED${NC}"
    return 1
  fi
}

# Function to check Postgres tables
check_postgres() {
  echo -n "Checking PostgreSQL tables... "
  
  tables=$(docker exec postgres_db psql -U postgres -c "\dt" | grep -E 'klienci|pracownicy|projekty' | wc -l)
  
  if [ "$tables" -ge 3 ]; then
    echo -e "${GREEN}OK ($tables tables found)${NC}"
    # Sample data from tables
    echo "Sample data from tables:"
    docker exec postgres_db psql -U postgres -c "SELECT * FROM klienci LIMIT 3;"
    return 0
  else
    echo -e "${RED}FAILED (Only $tables tables found)${NC}"
    return 1
  fi
}

# Function to check Kafka topics
check_kafka_topics() {
  echo -n "Checking Kafka topics... "
  
  topics=$(docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list | grep -c "dbserver1")
  
  if [ "$topics" -ge 1 ]; then
    echo -e "${GREEN}OK ($topics Debezium topics found)${NC}"
    echo "Kafka topics:"
    docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list
    return 0
  else
    echo -e "${RED}FAILED (No Debezium topics found)${NC}"
    return 1
  fi
}

# Function to check Debezium connectors
check_debezium() {
  echo -n "Checking Debezium connectors... "
  
  status=$(curl -s http://localhost:8083/connectors)
  
  if [[ $status == *"klienci"* ]]; then
    echo -e "${GREEN}OK (Connectors found)${NC}"
    echo "Connector details:"
    curl -s http://localhost:8083/connectors | jq . || echo "$status"
    return 0
  else
    echo -e "${YELLOW}WARNING (Connectors not visible or not created yet)${NC}"
    echo "You may need to create connectors by running setup_debezium.py"
    return 1
  fi
}

# Function to check Spark Master
check_spark_master() {
  echo -n "Checking Spark Master UI... "
  
  if curl -s http://localhost:8080 | grep -q "Spark Master"; then
    echo -e "${GREEN}OK${NC}"
    echo "Spark Master is running"
    return 0
  else
    echo -e "${RED}FAILED${NC}"
    return 1
  fi
}

# Function to check MinIO
check_minio() {
  echo -n "Checking MinIO API... "
  
  if curl -s http://localhost:9000/minio/health/live | grep -q "OK"; then
    echo -e "${GREEN}OK${NC}"
    echo "MinIO buckets:"
    docker run --rm --network="host" minio/mc config host add myminio http://localhost:9000 minio minio123 >/dev/null 2>&1
    docker run --rm --network="host" minio/mc ls myminio/ 2>/dev/null || echo "No buckets or unauthorized"
    return 0
  else
    echo -e "${RED}FAILED${NC}"
    return 1
  fi
}

# Main test sequence
echo -e "\n${YELLOW}1. Checking Container Status${NC}"
check_container "postgres_db"
check_container "kafka"
check_container "zookeeper"
check_container "debezium"
check_container "spark-master"
check_container "spark-worker"
check_container "minio"
check_container "spark-app"

echo -e "\n${YELLOW}2. Checking Component Accessibility${NC}"
check_port "PostgreSQL" "localhost" "5432"
check_port "Kafka" "localhost" "9092"
check_port "Zookeeper" "localhost" "2181"
check_port "Debezium Connect" "localhost" "8083"
check_port "Spark Master" "localhost" "8080"
check_port "Spark Worker" "localhost" "8081"
check_port "MinIO API" "localhost" "9000"
check_port "MinIO Console" "localhost" "9001"

echo -e "\n${YELLOW}3. Checking Component Functionality${NC}"
check_postgres
check_kafka_topics
check_debezium
check_spark_master
check_minio

echo -e "\n${YELLOW}4. Final Status Summary${NC}"
docker-compose ps

echo -e "\n${YELLOW}5. Logs from failing services${NC}"
# Check if any services are unhealthy and show logs
for service in postgres_db kafka zookeeper debezium spark-master spark-worker minio spark-app; do
  status=$(docker inspect --format='{{.State.Health.Status}}' $service 2>/dev/null)
  if [[ "$status" == "unhealthy" ]]; then
    echo -e "${RED}$service is unhealthy. Recent logs:${NC}"
    docker logs --tail 20 $service
  fi
done

echo -e "\n${YELLOW}===== Test Script Complete =====${NC}"
echo "You can run individual tests or check specific logs for more details."