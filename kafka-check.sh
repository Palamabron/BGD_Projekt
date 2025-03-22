#!/bin/bash
# Script to check Kafka health and connectivity

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}===== Kafka Health Check =====${NC}"

# Check if Kafka container exists
if [ ! "$(docker ps -q -f name=kafka)" ]; then
    echo -e "${RED}Kafka container is not running!${NC}"
    
    # Check if it existed but stopped
    if [ "$(docker ps -aq -f status=exited -f name=kafka)" ]; then
        echo -e "${YELLOW}Kafka container exists but exited. Checking logs:${NC}"
        docker logs kafka
        
        echo -e "\n${YELLOW}Attempting to restart Kafka...${NC}"
        docker start kafka
        sleep 10
        
        if [ "$(docker ps -q -f name=kafka)" ]; then
            echo -e "${GREEN}Kafka successfully restarted.${NC}"
        else
            echo -e "${RED}Failed to restart Kafka.${NC}"
        fi
    else
        echo -e "${YELLOW}Kafka container does not exist. You may need to run:${NC}"
        echo "docker-compose up -d kafka"
    fi
else
    echo -e "${GREEN}Kafka container is running.${NC}"
    
    # Get Kafka container IP
    KAFKA_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' kafka)
    echo -e "Kafka IP address: ${KAFKA_IP}"
    
    # Test Kafka connectivity
    echo -e "\n${YELLOW}Testing Kafka connectivity:${NC}"
    docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list
    
    # Add kafka IP to hosts file in Debezium container if needed
    echo -e "\n${YELLOW}Adding Kafka IP to Debezium hosts file:${NC}"
    if [ "$(docker ps -q -f name=debezium)" ]; then
        docker exec debezium bash -c "echo \"$KAFKA_IP kafka\" >> /etc/hosts"
        echo -e "${GREEN}Added Kafka IP to Debezium hosts file.${NC}"
        
        # Restart Debezium to pick up the changes
        echo -e "\n${YELLOW}Restarting Debezium container...${NC}"
        docker restart debezium
        echo -e "${GREEN}Debezium restarted.${NC}"
    else
        echo -e "${RED}Debezium container is not running.${NC}"
    fi
fi

echo -e "\n${YELLOW}===== Check Complete =====${NC}"