# Real-time Data Pipeline with Change Data Capture (CDC)

## 📋 Quick Start Guide

```bash
# Clone the repository
git clone <repository-url>
cd <project-directory>

# Start all services
docker-compose up -d

# Check if all services are running
docker-compose ps

# Test the pipeline
./test_pipeline.sh

# Check pipeline status
python debug_pipeline.py
```

## 🔍 What This Project Does

This project implements a comprehensive real-time data pipeline that:

1. **Captures changes** from a PostgreSQL database in real-time
2. **Streams them** through Kafka 
3. **Processes them** with Apache Spark
4. **Stores results** in MinIO (S3-compatible storage)

Ideal for building real-time analytics, data warehousing, and event-driven architectures.

## 🏗️ Architecture Overview

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│              │    │              │    │              │    │              │    │              │
│  PostgreSQL  │───▶│   Debezium   │───▶│    Kafka    │───▶│    Spark    │───▶│    MinIO     │
│  (WAL CDC)   │    │  (Connectors)│    │   (Topics)   │    │ (Processing) │    │  (Storage)   │
│              │    │              │    │              │    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       ▲
       │
┌──────────────┐
│  CSV Import  │
│  Application │
└──────────────┘
```

## 📁 Project Structure

```
├── csv_files/               # Sample data files to be imported
│   ├── klienci.csv          # Customer data
│   ├── klienci2.csv         # Additional customer data
│   ├── pracownicy.csv       # Employee data
│   └── projekty.csv         # Project data
│
├── spark-app/               # Spark application code
│   ├── Dockerfile           # Spark container configuration
│   ├── entrypoint.sh        # Spark app startup script
│   ├── requirements.txt     # Python dependencies for Spark
│   ├── setup_debezium.py    # Script to configure Debezium
│   ├── setup_minio.py       # Script to setup MinIO buckets
│   └── spark_processor.py   # Spark streaming job
│
├── debug_pipeline.py        # Pipeline troubleshooting utility
├── docker-compose.yml       # Docker services configuration
├── docker-network-diagnostic.sh # Network troubleshooting script
├── Dockerfile               # Main app Dockerfile
├── import_csv_to_postgres.py # CSV to PostgreSQL import script
├── kafka-check.sh           # Kafka health check script
├── pipeline-test.sh         # Pipeline component test script
├── postgresql.conf          # PostgreSQL CDC configuration
├── README.md                # This documentation
├── requirements.txt         # Python dependencies
└── test_pipeline.sh         # End-to-end pipeline test script
```

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.10+
- Git (for cloning the repository)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd <project-directory>
   ```

2. **Start the services**
   ```bash
   # Start all containers at once
   docker-compose up -d
   
   # Or start services in order to avoid dependency issues
   docker-compose up -d zookeeper
   sleep 10
   docker-compose up -d kafka
   sleep 20
   docker-compose up -d postgres_db
   sleep 10
   docker-compose up -d minio spark-master spark-worker
   sleep 5
   docker-compose up -d debezium
   sleep 20
   docker-compose up -d csv_import_app spark-app
   ```

3. **Verify the setup**
   ```bash
   # Check if all containers are running
   docker-compose ps
   
   # Run the debugging utility to check component status
   python debug_pipeline.py
   ```

## 💡 How It Works

### 1. Data Import from CSV

The `csv_import_app` container reads CSV files from the `csv_files` directory and imports them into PostgreSQL.

**Key Files:**
- `import_csv_to_postgres.py`: The main script that handles CSV import
- `csv_files/*.csv`: Source data files

**How it works:**
```python
# From import_csv_to_postgres.py
def import_csv_to_postgres(folder, db_user, db_password, db_host, db_port, db_name):
    connection_url = f'postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
    engine = create_engine(connection_url)
    
    # Process each CSV file in the folder
    for file in sorted(os.listdir(folder)):
        if file.endswith('.csv'):
            table_name = os.path.splitext(file)[0].rstrip("0123456789")
            # Table name is derived from file name (stripped of numbers)
            # So klienci.csv and klienci2.csv both go to table 'klienci'
            
            # [Code to read CSV and import to PostgreSQL]
```

**Running manually:**
```bash
# Import CSV files to PostgreSQL
docker-compose run csv_import_app
```

### 2. Change Data Capture with Debezium

Debezium monitors PostgreSQL's transaction log and captures changes as they happen.

**Key Files:**
- `spark-app/setup_debezium.py`: Configures Debezium connectors
- `postgresql.conf`: Configures PostgreSQL for logical replication

**How it works:**
```python
# From setup_debezium.py
klienci_connector = {
    "name": "klienci-connector",
    "config": {
        "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
        "database.hostname": "postgres_db",
        "database.port": "5432",
        "database.user": "postgres",
        "database.password": "password",
        "database.dbname": "postgres",
        "database.server.name": "dbserver1",
        "table.include.list": "public.klienci",  # Which table to monitor
        "plugin.name": "pgoutput",               # PostgreSQL output plugin
        "topic.prefix": "dbserver1",             # Kafka topic prefix
        "slot.name": "debezium_klienci"          # Replication slot name
    }
}
```

**PostgreSQL CDC configuration:**
```
# postgresql.conf settings for CDC
wal_level = logical              # Enable logical decoding
max_wal_senders = 10             # Max number of WAL sender processes
max_replication_slots = 10       # Max number of replication slots
```

**Setting up manually:**
```bash
# Create a Debezium connector for a table
curl -X POST -H "Content-Type: application/json" -d @connector-config.json http://localhost:8083/connectors
```

### 3. Kafka Message Streaming

Kafka receives change events from Debezium and acts as the central message bus.

**Key Files:**
- `docker-compose.yml`: Configures Kafka and Zookeeper
- `kafka-check.sh`: Utility script for checking Kafka health

**How it works:**
- Debezium publishes change events to topics named `dbserver1.public.<table_name>`
- Events contain the full state of the record before and after the change
- Kafka maintains these events in order and makes them available to consumers

**Checking Kafka manually:**
```bash
# List Kafka topics
docker exec kafka kafka-topics --bootstrap-server kafka:9092 --list

# View messages in a topic
docker exec kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic dbserver1.public.klienci --from-beginning --max-messages 3
```

### 4. Real-time Processing with Spark

Spark reads the change events from Kafka and processes them in near real-time.

**Key Files:**
- `spark-app/spark_processor.py`: Spark streaming application
- `spark-app/entrypoint.sh`: Script to start the Spark job

**How it works:**
```python
# From spark_processor.py
# Read from Kafka
kafka_df = spark \
    .readStream \
    .format("kafka") \
    .options(**kafka_options) \
    .load()

# Process data and write to MinIO
query = kafka_df \
    .selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)", "topic", "partition", "offset", "timestamp") \
    .writeStream \
    .format("parquet") \
    .option("checkpointLocation", "/tmp/checkpoint-all") \
    .option("path", "s3a://processed-data/raw-kafka-data") \
    .trigger(processingTime="10 seconds") \
    .start()
```

**Checking Spark manually:**
```bash
# Check Spark logs
docker logs spark-app

# Access Spark UI (if available)
# Open in browser: http://localhost:8080
```

### 5. Data Storage in MinIO

Processed data is stored in MinIO in organized buckets.

**Key Files:**
- `spark-app/setup_minio.py`: Creates MinIO buckets
- `spark-app/spark_processor.py`: Configures Spark to write to MinIO

**How it works:**
```python
# From setup_minio.py
# Configure MinIO client
s3_client = boto3.client(
    's3',
    endpoint_url='http://minio:9000',
    aws_access_key_id='minio',
    aws_secret_access_key='minio123',
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)

# Create buckets
s3_client.create_bucket(Bucket='processed-data')
```

**Accessing MinIO manually:**
```bash
# List MinIO buckets
docker exec minio mc alias set myminio http://localhost:9000 minio minio123
docker exec minio mc ls myminio/

# Browse MinIO console
# Open in browser: http://localhost:9001
# Login with: minio / minio123
```

## 🔧 Debugging and Troubleshooting

This project includes several utility scripts to help you diagnose and fix issues:

### 1. Pipeline Debugging Utility

The `debug_pipeline.py` script is your Swiss Army knife for checking the entire pipeline.

**Usage:**
```bash
# Check all components
python debug_pipeline.py

# Check specific components
python debug_pipeline.py --component postgres
python debug_pipeline.py --component kafka
python debug_pipeline.py --component debezium
python debug_pipeline.py --component spark
python debug_pipeline.py --component minio
```

**What it checks:**
- PostgreSQL: Table contents, replication slots
- Kafka: Topics, messages
- Debezium: Connector status, failed tasks
- Spark: Master status, workers, applications
- MinIO: Buckets, objects

### 2. Network Diagnostics

The `docker-network-diagnostic.sh` script helps diagnose network connectivity issues.

**Usage:**
```bash
./docker-network-diagnostic.sh
```

**What it checks:**
- Docker networks
- Container IP addresses
- DNS resolution between containers
- Kafka connectivity

### 3. Kafka Health Check

The `kafka-check.sh` script specifically checks Kafka status.

**Usage:**
```bash
./kafka-check.sh
```

**What it checks:**
- Kafka container status
- Connectivity to broker
- Topic listing
- Adds Kafka IP to Debezium's hosts file if needed

### 4. Pipeline Testing

The `test_pipeline.sh` script runs a full end-to-end test of the pipeline.

**Usage:**
```bash
./test_pipeline.sh
```

**What it does:**
- Inserts test data into PostgreSQL
- Checks Kafka topics for messages
- Verifies Debezium connector status
- Checks MinIO for processed data

## 🧰 Common Tasks

### Adding a New Table to the Pipeline

1. **Create the table in PostgreSQL**
   ```sql
   CREATE TABLE categories (
     id SERIAL PRIMARY KEY,
     name VARCHAR(100),
     description TEXT
   );
   ```

2. **Create a Debezium connector for the table**
   ```bash
   curl -X POST -H "Content-Type: application/json" -d '{
     "name": "categories-connector",
     "config": {
       "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
       "database.hostname": "postgres_db",
       "database.port": "5432",
       "database.user": "postgres",
       "database.password": "password",
       "database.dbname": "postgres",
       "database.server.name": "dbserver1",
       "table.include.list": "public.categories",
       "plugin.name": "pgoutput",
       "topic.prefix": "dbserver1",
       "slot.name": "debezium_categories"
     }
   }' http://localhost:8083/connectors
   ```

3. **Update Spark to process the new topic**
   Edit `spark-app/spark_processor.py` to include the new topic in the subscription:
   ```python
   kafka_options = {
       "kafka.bootstrap.servers": "kafka:9092",
       "subscribe": "dbserver1.public.klienci,dbserver1.public.pracownicy,dbserver1.public.projekty,dbserver1.public.categories",
       "startingOffsets": "earliest"
   }
   ```

### Adding Custom Transformations

Edit `spark-app/spark_processor.py` to add custom processing logic:

```python
# Example: Parse JSON and perform aggregations
from pyspark.sql.functions import from_json, col

# Define schema for your data
schema = ...

# Parse JSON data
parsed_df = kafka_df \
    .selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.payload.after.*")

# Apply transformations
transformed_df = parsed_df \
    .groupBy("some_column") \
    .agg(...)

# Write to MinIO
query = transformed_df \
    .writeStream \
    .format("parquet") \
    .option("checkpointLocation", "/tmp/checkpoint-transformed") \
    .option("path", "s3a://processed-data/transformed-data") \
    .start()
```

## 🛠️ Troubleshooting Common Issues

### 1. Debezium Connectors Failing

**Symptoms:**
- Connector status shows "FAILED"
- Error about "replication slot already exists"

**Solution:**
```bash
# Check replication slots
docker exec postgres_db psql -U postgres -c "SELECT * FROM pg_replication_slots;"

# Drop existing slot if needed
docker exec postgres_db psql -U postgres -c "SELECT pg_drop_replication_slot('debezium_klienci');"

# Recreate the connector
curl -X DELETE http://localhost:8083/connectors/klienci-connector
# Then recreate with POST request
```

### 2. Kafka Connectivity Issues

**Symptoms:**
- Services can't connect to Kafka
- "UnknownHostException" in logs

**Solution:**
```bash
# Run the Kafka check script
./kafka-check.sh

# Or manually fix host resolution
docker exec debezium bash -c "echo \"$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' kafka) kafka\" >> /etc/hosts"
```

### 3. PostgreSQL WAL Configuration

**Symptoms:**
- CDC not working
- "wal_level must be logical" errors

**Solution:**
```bash
# Check current WAL level
docker exec postgres_db psql -U postgres -c "SHOW wal_level;"

# If not set to logical, you need to recreate the container with proper config
# Make sure postgresql.conf has:
# wal_level = logical
# Then restart PostgreSQL
docker-compose restart postgres_db
```

### 4. Spark Processing Issues

**Symptoms:**
- No data in MinIO
- Errors in Spark logs

**Solution:**
```bash
# Check Spark logs
docker logs spark-app

# Verify Kafka topics exist and have data
docker exec kafka kafka-topics --bootstrap-server kafka:9092 --list
docker exec kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic dbserver1.public.klienci --from-beginning --max-messages 1

# Restart the Spark app
docker-compose restart spark-app
```

## 📊 Monitoring the Pipeline

### Checking Component Status

```bash
# Overall pipeline status
python debug_pipeline.py

# Docker container status
docker-compose ps

# PostgreSQL tables and data
docker exec postgres_db psql -U postgres -c "\dt"
docker exec postgres_db psql -U postgres -c "SELECT COUNT(*) FROM klienci;"

# Kafka topics
docker exec kafka kafka-topics --bootstrap-server kafka:9092 --list

# Debezium connectors
curl -s http://localhost:8083/connectors | jq .

# MinIO buckets and objects
docker exec minio mc ls myminio/processed-data/ --recursive
```

### Viewing Logs

```bash
# View logs for specific services
docker logs postgres_db
docker logs kafka
docker logs debezium
docker logs spark-app
docker logs minio

# Follow logs in real-time
docker logs -f spark-app
```

## 📈 Performance Optimization

### PostgreSQL Optimization

Edit `postgresql.conf` to tune PostgreSQL performance:

```
# Memory settings
shared_buffers = 256MB  # Increase for better caching (25% of RAM)
work_mem = 64MB         # Increase for complex queries

# WAL settings
wal_buffers = 16MB      # Helps with write-heavy workloads
checkpoint_timeout = 10min  # Less frequent checkpoints
```

### Kafka Optimization

```bash
# Increase partition count for parallelism
docker exec kafka kafka-topics --bootstrap-server kafka:9092 --alter --topic dbserver1.public.klienci --partitions 3
```

### Spark Optimization

Edit `docker-compose.yml` to give Spark more resources:

```yaml
spark-worker:
  environment:
    - SPARK_WORKER_MEMORY=2g
    - SPARK_WORKER_CORES=2
```

## 🔄 Extending the Pipeline

### Adding Data Quality Checks

```python
# In spark_processor.py
from pyspark.sql.functions import col, when, count

# Check for missing values
df_quality = df_parsed \
    .select([count(when(col(c).isNull(), c)).alias(c) for c in df_parsed.columns])

# Log quality metrics
df_quality \
    .writeStream \
    .format("console") \
    .outputMode("complete") \
    .start()
```

### Adding Real-time Analytics

```python
# In spark_processor.py
# Calculate real-time metrics
metrics_df = df_parsed \
    .withWatermark("timestamp", "10 minutes") \
    .groupBy(window(col("timestamp"), "5 minutes"), col("event_type")) \
    .count()

# Output to separate MinIO location
metrics_df \
    .writeStream \
    .format("parquet") \
    .option("path", "s3a://processed-data/metrics") \
    .option("checkpointLocation", "/tmp/checkpoint-metrics") \
    .start()
```

## 📚 Additional Resources

- [Debezium Documentation](https://debezium.io/documentation/)
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Apache Spark Documentation](https://spark.apache.org/docs/latest/)
- [MinIO Documentation](https://docs.min.io/)

## 📝 License

[Your license information here]

## 👥 Contributors

[Your contributor information here]