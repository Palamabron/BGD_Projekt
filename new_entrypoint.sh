#!/bin/bash

# Wait for other services to be ready
echo "Waiting for services to be ready..."
sleep 30

# Setup MinIO bucket
echo "Setting up MinIO bucket..."
python /app/setup_minio.py

# Setup Debezium connector
echo "Setting up Debezium connector..."
python /app/setup_debezium.py

# Run Spark streaming job in the background
echo "Running Spark streaming job..."
spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0,org.apache.hadoop:hadoop-aws:3.3.1 \
  /app/spark_processor.py &

# Wait a bit for initial data collection
sleep 60

# Run batch processor periodically
echo "Setting up batch processing job..."
while true; do
  echo "Running batch processor..."
  spark-submit \
    --master spark://spark-master:7077 \
    --packages org.apache.hadoop:hadoop-aws:3.3.1 \
    /app/batch_processor.py
  
  echo "Batch processing completed. Sleeping for 5 minutes..."
  sleep 300
done
