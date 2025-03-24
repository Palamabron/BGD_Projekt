#!/bin/bash

# Funkcja do logowania z timestampem
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Dodaj wpisy do /etc/hosts dla wszystkich serwisów
setup_hosts() {
  log "Dodawanie wpisów do /etc/hosts..."
  
  # Dodaj wpis dla Kafka
  echo "172.18.0.3 kafka" >> /etc/hosts
  log "Dodano kafka -> 172.18.0.3 do /etc/hosts"
}

# Czekaj na dostępność serwisów
log "Czekam na uruchomienie wszystkich serwisów..."
sleep 60

# Dodaj wpisy do hostów
setup_hosts

# Ustawienie bucketów MinIO
log "Konfiguracja bucketu MinIO..."
python /app/setup_minio.py

# Konfiguracja Debezium
log "Konfiguracja konektorów Debezium..."
python /app/setup_debezium.py

# Dłuższe oczekiwanie na utworzenie slotów i tematów Kafka
log "Czekam na inicjalizację Debezium i utworzenie tematów Kafka..."
sleep 120

# Test połączenia z Kafka bez użycia nc
log "Sprawdzanie połączenia z Kafka..."
attempts=0
max_attempts=5
kafka_ready=false

while [ $attempts -lt $max_attempts ] && [ "$kafka_ready" = false ]; do
  attempts=$((attempts+1))
  log "Próba połączenia z Kafka ($attempts/$max_attempts)..."
  
  # Używam --version jako prostego testu połączenia
  if kafka-topics.sh --bootstrap-server kafka:9092 --version >/dev/null 2>&1; then
    kafka_ready=true
    log "Połączenie z Kafka działa!"
  else
    log "Problem z połączeniem do Kafka. Czekam..."
    sleep 30
  fi
done

# Uruchom zadanie strumieniowe Spark
log "Uruchamianie przetwarzania strumieniowego Spark..."
KAFKA_TOPICS="dbserver1.public.klienci,dbserver1.public.pracownicy,dbserver1.public.projekty"
log "Używane tematy Kafka: $KAFKA_TOPICS"

SPARK_STREAM_CMD="spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0,org.apache.hadoop:hadoop-aws:3.3.1 \
  --conf spark.driver.host=$(hostname) \
  --conf spark.executor.extraJavaOptions=-Dsun.net.inetaddr.ttl=30 \
  --conf spark.driver.extraJavaOptions=-Dsun.net.inetaddr.ttl=30 \
  --conf spark.sql.streaming.schemaInference=true \
  /app/spark_processor.py"

log "Wykonuję: $SPARK_STREAM_CMD"
$SPARK_STREAM_CMD &
SPARK_STREAM_PID=$!

# Sprawdź, czy proces się uruchomił
if ps -p $SPARK_STREAM_PID > /dev/null; then
  log "Proces przetwarzania strumieniowego uruchomiony z PID: $SPARK_STREAM_PID"
else
  log "BŁĄD: Proces przetwarzania strumieniowego nie uruchomił się!"
fi

# Czekaj na zebranie danych
log "Czekam na zebranie początkowych danych..."
sleep 180

# Uruchamiaj przetwarzanie wsadowe cyklicznie
log "Uruchamianie cyklicznego przetwarzania wsadowego..."
while true; do
  log "Uruchamianie przetwarzania wsadowego..."
  SPARK_BATCH_CMD="spark-submit \
    --master spark://spark-master:7077 \
    --packages org.apache.hadoop:hadoop-aws:3.3.1 \
    --conf spark.driver.host=$(hostname) \
    --conf spark.sql.parquet.binaryAsString=true \
    /app/batch_processor.py"
  
  log "Wykonuję: $SPARK_BATCH_CMD"
  $SPARK_BATCH_CMD
  
  # Sprawdź, czy dane zostały zapisane w MinIO
  log "Sprawdzam, czy dane zostały zapisane w MinIO..."
  sleep 10
  
  log "Przetwarzanie wsadowe zakończone. Czekam 5 minut..."
  sleep 300
done