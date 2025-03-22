#!/bin/bash
# Docker Network Diagnostic Script

# Colors for better readability
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}===== Docker Network Diagnostic =====${NC}"

# List all Docker networks
echo -e "\n${YELLOW}1. Docker Networks${NC}"
docker network ls

# Check default network
DEFAULT_NETWORK="bgd_projekt_default"
echo -e "\n${YELLOW}2. Inspecting Default Network (${DEFAULT_NETWORK})${NC}"
docker network inspect ${DEFAULT_NETWORK}

# Check all running containers
echo -e "\n${YELLOW}3. Running Containers${NC}"
docker ps

# Check containers in the default network
echo -e "\n${YELLOW}4. Containers in Default Network${NC}"
docker network inspect ${DEFAULT_NETWORK} -f '{{range .Containers}}{{.Name}} {{.IPv4Address}}{{println}}{{end}}'

# Test DNS resolution from each critical container
echo -e "\n${YELLOW}5. Testing DNS Resolution${NC}"

# Function to test DNS resolution from a container
test_dns() {
  container=$1
  target=$2
  
  echo -e "${YELLOW}Testing DNS resolution from ${container} to ${target}:${NC}"
  docker exec ${container} ping -c 1 ${target} || echo -e "${RED}Failed to ping ${target} from ${container}${NC}"
}

# Test DNS resolution in both directions
test_dns "debezium" "kafka"
test_dns "kafka" "debezium"
test_dns "debezium" "postgres_db"
test_dns "postgres_db" "debezium"

# Check if kafka is running and listening
echo -e "\n${YELLOW}6. Checking Kafka Status${NC}"
docker exec kafka bash -c "netstat -tulpn | grep 9092" || echo -e "${RED}Kafka might not be listening on port 9092${NC}"

# Check Kafka topics
echo -e "\n${YELLOW}7. Checking Kafka Topics${NC}"
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list || echo -e "${RED}Failed to list Kafka topics${NC}"

# Check Debezium logs for connectivity issues
echo -e "\n${YELLOW}8. Checking Debezium Logs for Connectivity Issues${NC}"
docker logs debezium | grep -i "kafka" | grep -i "error" | tail -20

echo -e "\n${YELLOW}===== Diagnostic Complete =====${NC}"
echo "If you see DNS resolution errors, consider restarting the Docker network or recreating the containers."
echo "You can also try adding explicit 'links:' in your docker-compose.yml to ensure connectivity."