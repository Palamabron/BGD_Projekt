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

# Run Spark job
echo "Running Spark job..."
spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0,org.apache.hadoop:hadoop-aws:3.3.1 \
  /app/spark_processor.py