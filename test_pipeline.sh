#!/bin/bash
# Test the full pipeline from PostgreSQL to Kafka to MinIO

# Colors for better readability
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}===== Data Pipeline Test =====${NC}"

# 1. Check all containers are running
echo -e "\n${YELLOW}1. Checking Container Status${NC}"
docker-compose ps

# 2. Check PostgreSQL tables
echo -e "\n${YELLOW}2. Checking PostgreSQL Tables${NC}"
docker exec postgres_db psql -U postgres -c "\dt"

# 3. Insert test data into PostgreSQL
echo -e "\n${YELLOW}3. Inserting Test Data into PostgreSQL${NC}"
docker exec postgres_db psql -U postgres -c "
INSERT INTO klienci (nazwa, email, kraj, telefon) 
VALUES 
('Test Klient 1', 'klient1@example.com', 'Polska', '123-456-789'),
('Test Klient 2', 'klient2@example.com', 'Niemcy', '987-654-321');

INSERT INTO pracownicy (imie, nazwisko, email, wiek, stanowisko)
VALUES
('Jan', 'Kowalski', 'jan.kowalski@example.com', 35, 'Developer'),
('Anna', 'Nowak', 'anna.nowak@example.com', 28, 'Designer');

INSERT INTO projekty (nazwa, opis, data_rozpoczecia, data_zakonczenia)
VALUES
('Projekt A', 'Testowy projekt A', '2025-01-01', '2025-12-31'),
('Projekt B', 'Testowy projekt B', '2025-02-01', '2025-11-30');
"

echo -e "\n${YELLOW}4. Verifying Data in PostgreSQL${NC}"
docker exec postgres_db psql -U postgres -c "SELECT * FROM klienci;"
docker exec postgres_db psql -U postgres -c "SELECT * FROM pracownicy;"
docker exec postgres_db psql -U postgres -c "SELECT * FROM projekty;"

# 4. Check Kafka topics
echo -e "\n${YELLOW}5. Checking Kafka Topics${NC}"
docker exec kafka kafka-topics --bootstrap-server kafka:9092 --list

# 5. Check messages in Kafka topics
echo -e "\n${YELLOW}6. Checking Messages in Kafka Topics${NC}"
echo -e "Messages in dbserver1.public.klienci topic:"
docker exec kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic dbserver1.public.klienci --from-beginning --max-messages 2

echo -e "\nMessages in dbserver1.public.pracownicy topic:"
docker exec kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic dbserver1.public.pracownicy --from-beginning --max-messages 2

echo -e "\nMessages in dbserver1.public.projekty topic:"
docker exec kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic dbserver1.public.projekty --from-beginning --max-messages 2

# 6. Check Debezium connector status
echo -e "\n${YELLOW}7. Checking Debezium Connector Status${NC}"
curl -s http://localhost:8083/connectors | jq .
for connector in $(curl -s http://localhost:8083/connectors | jq -r '.[]'); do
  echo -e "\nStatus for $connector:"
  curl -s http://localhost:8083/connectors/$connector/status | jq .
done

# 7. Check MinIO
echo -e "\n${YELLOW}8. Checking MinIO Buckets${NC}"
docker exec minio mc alias set myminio http://localhost:9000 minio minio123
docker exec minio mc ls myminio/

# 8. Wait for Spark to process data
echo -e "\n${YELLOW}9. Waiting for Spark to Process Data (30 seconds)${NC}"
echo "This gives Spark time to process the data..."
sleep 30

# 9. Check MinIO for processed data
echo -e "\n${YELLOW}10. Checking MinIO for Processed Data${NC}"
docker exec minio mc ls myminio/processed-data/ || echo -e "${RED}No processed data found in MinIO${NC}"

echo -e "\n${YELLOW}===== Test Complete =====${NC}"
echo "If you don't see data in MinIO, check the Spark logs for any errors:"
echo "docker logs spark-app"