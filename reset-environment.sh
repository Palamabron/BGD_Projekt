#!/bin/bash
# Skrypt do pełnego resetowania środowiska (zarówno Kafka jak i PostgreSQL)

# Kolory do formatowania wyjścia
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Pełne resetowanie środowiska ===${NC}"

# 1. Check if PostgreSQL is running, and if so, clean publications and slots
if docker ps | grep -q postgres_db; then
  echo -e "${BLUE}PostgreSQL is running. Cleaning publications and replication slots...${NC}"
  
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

  # Drop replication slots - Fixed to avoid ambiguous column reference
  echo -e "${BLUE}Dropping PostgreSQL replication slots...${NC}"
  docker exec postgres_db psql -U postgres -c "
  DO \$\$
  DECLARE
    slot_record record;
  BEGIN
    FOR slot_record IN (SELECT slot_name FROM pg_replication_slots)
    LOOP
      EXECUTE 'SELECT pg_drop_replication_slot(''' || slot_record.slot_name || ''');';
      RAISE NOTICE 'Dropped replication slot %', slot_record.slot_name;
    END LOOP;
  END;
  \$\$;
  "
  
  echo -e "${GREEN}PostgreSQL publications and replication slots cleaned.${NC}"
fi

# 2. Zatrzymaj wszystkie kontenery
echo -e "${BLUE}1. Zatrzymywanie wszystkich kontenerów...${NC}"
docker-compose down

# 3. Usuń wszystkie woluminy
echo -e "${BLUE}2. Usuwanie wszystkich woluminów...${NC}"
docker volume rm kafka_data_fixed 2>/dev/null || true
docker volume rm kafka_data_clean 2>/dev/null || true
docker volume rm bgd_projekt_pgdata 2>/dev/null || true
docker volume rm bgd_projekt_minio_data 2>/dev/null || true

echo -e "${GREEN}Wszystkie woluminy zostały usunięte.${NC}"

# 4. Utwórz skrypty inicjalizacyjne
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

# 5. Uruchom Zookeeper i poczekaj na jego gotowość
echo -e "${BLUE}4. Uruchamianie Zookeeper...${NC}"
docker-compose up -d zookeeper
sleep 15
echo -e "${GREEN}Zookeeper uruchomiony.${NC}"

# 6. Uruchom Kafka
echo -e "${BLUE}5. Uruchamianie Kafka...${NC}"
docker-compose up -d kafka
echo -e "${YELLOW}Czekam 30 sekund na uruchomienie Kafka...${NC}"
sleep 30

# 7. Sprawdź stan Kafka
echo -e "${BLUE}6. Sprawdzanie stanu Kafka...${NC}"
docker ps | grep kafka

# 8. Uruchom PostgreSQL
echo -e "${BLUE}7. Uruchamianie PostgreSQL...${NC}"
docker-compose up -d postgres_db
echo -e "${YELLOW}Czekam 15 sekund na uruchomienie PostgreSQL...${NC}"
sleep 15

# 9. Uruchom pozostałe kontenery
echo -e "${BLUE}8. Uruchamianie pozostałych kontenerów...${NC}"
docker-compose up -d
echo -e "${YELLOW}Czekam 20 sekund na uruchomienie wszystkich kontenerów...${NC}"
sleep 20

# 10. Sprawdź stan wszystkich kontenerów
echo -e "${BLUE}9. Sprawdzanie stanu wszystkich kontenerów...${NC}"
docker-compose ps

# 11. Importuj dane CSV do PostgreSQL
echo -e "${BLUE}10. Uruchamianie aplikacji importu CSV...${NC}"
docker-compose up -d csv_import_app
sleep 10  # Daj czas na import danych

echo -e "${GREEN}Gotowe! Środowisko zostało całkowicie zresetowane.${NC}"
echo -e "${YELLOW}Możesz teraz uruchomić test_pipeline.sh, aby przetestować cały pipeline.${NC}"