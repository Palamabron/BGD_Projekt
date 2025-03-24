#!/bin/bash
# Skrypt do naprawy i uruchomienia Kafka

# Kolory do formatowania wyjścia
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Skrypt naprawy dla Kafka ===${NC}"

# 1. Zatrzymaj wszystkie kontenery
echo -e "${BLUE}1. Zatrzymywanie wszystkich kontenerów...${NC}"
docker-compose down

# 2. Usuń wolumin Kafka
echo -e "${BLUE}2. Usuwanie woluminu Kafka...${NC}"
docker volume rm kafka_data_fixed 2>/dev/null || true
docker volume rm kafka_data_clean 2>/dev/null || true

# 3. Sprawdź i utwórz skrypt inicjalizacyjny dla Kafka
echo -e "${BLUE}3. Tworzenie uproszczonego skryptu inicjalizacyjnego Kafka...${NC}"
cat > kafka-init.sh << "EOF"
#!/bin/bash
# Prosty skrypt do inicjalizacji Kafka z czystym katalogiem danych

echo "=== Uproszczony skrypt inicjalizacyjny Kafka ==="

# Całkowicie usuń stary katalog danych, aby zapobiec problemom z niezgodnością cluster.id
rm -rf /var/lib/kafka/data/*
mkdir -p /var/lib/kafka/data
chmod -R 777 /var/lib/kafka/data

echo "Katalog danych został wyczyszczony i utworzony na nowo"

# Uruchom Kafka z czystym katalogiem danych
echo "Uruchamianie Kafka..."
exec /etc/confluent/docker/run
EOF

# Nadaj uprawnienia wykonywania
chmod +x kafka-init.sh
echo -e "${GREEN}Skrypt inicjalizacyjny Kafka utworzony i gotowy.${NC}"

# 4. Uruchom Zookeeper i poczekaj na jego gotowość
echo -e "${BLUE}4. Uruchamianie Zookeeper...${NC}"
docker-compose up -d zookeeper
sleep 15
echo -e "${GREEN}Zookeeper uruchomiony.${NC}"

# 5. Uruchom Kafka
echo -e "${BLUE}5. Uruchamianie Kafka...${NC}"
docker-compose up -d kafka
echo -e "${YELLOW}Czekam 30 sekund na uruchomienie Kafka...${NC}"
sleep 30

# 6. Sprawdź stan Kafka
echo -e "${BLUE}6. Sprawdzanie stanu Kafka...${NC}"
docker ps | grep kafka
docker logs kafka | tail -n 20

# 7. Uruchom pozostałe kontenery, jeśli Kafka działa
if [ "$(docker ps -q -f name=kafka -f status=running)" ]; then
    echo -e "${GREEN}Kafka działa! Uruchamianie pozostałych kontenerów...${NC}"
    
    # Uruchom PostgreSQL
    echo -e "${BLUE}Uruchamianie PostgreSQL...${NC}"
    docker-compose up -d postgres_db
    sleep 15
    
    # Uruchom pozostałe kontenery
    echo -e "${BLUE}Uruchamianie pozostałych kontenerów...${NC}"
    docker-compose up -d
    
    echo -e "${GREEN}Wszystkie kontenery zostały uruchomione.${NC}"
    
    # Pokaż stan kontenerów
    echo -e "${BLUE}Stan kontenerów:${NC}"
    docker-compose ps
else
    echo -e "${RED}Kafka nie uruchomił się poprawnie. Sprawdź logi:${NC}"
    docker logs kafka
    exit 1
fi

echo -e "${GREEN}Gotowe! Pipeline powinien teraz działać poprawnie.${NC}"
echo -e "${YELLOW}Możesz teraz uruchomić test_pipeline.sh, aby przetestować cały pipeline.${NC}"