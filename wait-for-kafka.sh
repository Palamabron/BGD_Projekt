#!/bin/bash
# Wait script for Kafka to be ready

MAX_ATTEMPTS=30
ATTEMPT=1

echo "Waiting for Kafka to be ready..."

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
  echo "Attempt $ATTEMPT of $MAX_ATTEMPTS"
  
  if docker exec kafka kafka-topics --bootstrap-server kafka:9092 --list > /dev/null 2>&1; then
    echo "✅ Kafka is ready!"
    exit 0
  fi
  
  echo "Kafka not ready yet, waiting 5 seconds..."
  sleep 5
  ATTEMPT=$((ATTEMPT+1))
done

echo "❌ Timeout waiting for Kafka to be ready"
exit 1