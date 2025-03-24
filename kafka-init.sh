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
