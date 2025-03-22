# Real-time Data Pipeline with Change Data Capture (CDC)

This project implements a comprehensive real-time data pipeline that captures changes from a PostgreSQL database, streams them through Kafka, processes them with Apache Spark, and stores the results in MinIO (S3-compatible storage).

## Architecture Overview

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

## Components in Detail

### 1. PostgreSQL Database
PostgreSQL serves as the primary data store with logical replication enabled to support Change Data Capture (CDC).

**Key Configuration:**
- **WAL (Write-Ahead Log) Level**: Set to `logical` to enable CDC
- **Replication Slots**: Created for each table being monitored
- **Tables**: klienci (customers), pracownicy (employees), projekty (projects)

**Configuration Example:**
```
# postgresql.conf settings for CDC
wal_level = logical
max_wal_senders = 10
max_replication_slots = 10
```

### 2. Debezium CDC Connectors
Debezium monitors the PostgreSQL transaction log and converts changes into events.

**Features:**
- **Publication Management**: Creates and manages PostgreSQL publications
- **Schema Handling**: Preserves original data schema in change events
- **Change Events**: Captures INSERT, UPDATE, DELETE operations with before/after states

**Connector Configuration Example:**
```json
{
  "name": "klienci-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres_db",
    "database.port": "5432",
    "database.user": "postgres",
    "database.password": "password",
    "database.dbname": "postgres",
    "database.server.name": "dbserver1",
    "table.include.list": "public.klienci",
    "plugin.name": "pgoutput",
    "topic.prefix": "dbserver1",
    "slot.name": "debezium_klienci",
    "publication.name": "dbz_publication_klienci"
  }
}
```

### 3. Apache Kafka
Kafka acts as the central message bus for streaming change events.

**Components:**
- **Topics**: Separate topics for each table (e.g., `dbserver1.public.klienci`)
- **Zookeeper**: Manages Kafka broker state and configurations
- **Brokers**: Handles message storage and delivery

**Topic Structure:**
- Raw change events in JSON format
- Contains both data and metadata about changes
- Preserves event ordering for each table

### 4. Apache Spark
Spark processes the streaming data from Kafka in near real-time.

**Processing Features:**
- **Structured Streaming**: Processes data in micro-batches
- **Schema Inference**: Automatically extracts and processes the Debezium schema
- **Transformations**: Aggregations, filtering, and enrichment of data
- **Output Modes**: Supports append, update, and complete output modes

**Processing Examples:**
```python
# Group customers by country
df_klienci_by_country = df_klienci \
    .groupBy("kraj") \
    .count()

# Calculate average age by position
df_avg_age_by_position = df_pracownicy \
    .groupBy("stanowisko") \
    .avg("wiek")
```

### 5. MinIO Storage
MinIO provides S3-compatible object storage for the processed data.

**Storage Features:**
- **Buckets**: Organized storage for different data types
- **Formats**: Supports Parquet, CSV, JSON, and other formats
- **Partitioning**: Data can be partitioned by time or other dimensions
- **Access Control**: Fine-grained access management

**Bucket Structure:**
- `processed-data/raw-kafka-data/`: Raw data from Kafka
- `processed-data/klienci-by-country/`: Aggregated customer data
- `processed-data/avg-age-by-position/`: Employee statistics

## Directory Structure

```
├── csv_files/               # Folder with CSV files
│   ├── klienci.csv          # Customer data
│   ├── pracownicy.csv       # Employee data
│   └── projekty.csv         # Project data
├── spark-app/               # Spark processing application
│   ├── Dockerfile           # Docker configuration for Spark
│   ├── entrypoint.sh        # Startup script
│   ├── requirements.txt     # Python dependencies
│   ├── setup_debezium.py    # Configuration for Debezium connectors
│   ├── setup_minio.py       # MinIO bucket setup
│   └── spark_processor.py   # Spark streaming application
├── debug_pipeline.py        # Utility for pipeline troubleshooting
├── docker-compose.yml       # Docker services configuration
├── import_csv_to_postgres.py # CSV to PostgreSQL import script
├── Dockerfile               # Main application Dockerfile
├── postgresql.conf          # PostgreSQL configuration
├── README.md                # This documentation file
├── requirements.txt         # Python dependencies
├── setup_pipeline.sh        # Pipeline initialization script
└── wait-for-kafka.sh        # Kafka readiness check script
```

## Setup and Deployment

### Prerequisites

- Docker and Docker Compose
- Python 3.10+
- CSV data files in `/csv_files` directory

### Step-by-Step Deployment

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd <project-directory>
   ```

2. **Configure PostgreSQL for CDC**
   Create a `postgresql.conf` file with logical replication enabled:
   ```bash
   cat > postgresql.conf << EOF
   # PostgreSQL configuration for CDC
   listen_addresses = '*'
   port = 5432
   max_connections = 100
   shared_buffers = 128MB
   wal_level = logical
   max_wal_senders = 10
   max_replication_slots = 10
   hot_standby = on
   EOF
   ```

3. **Start the infrastructure**
   ```bash
   # Launch all containers in the correct order
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

4. **Verify service health**
   ```bash
   # Check all containers are running
   docker-compose ps
   
   # Run the pipeline debugging utility
   python debug_pipeline.py
   ```

## Data Flow Process

### 1. CSV Import Process
The `csv_import_app` container automatically imports CSV files from the `csv_files` directory to PostgreSQL.

**How it works:**
1. Scans the `csv_files` directory for CSV files
2. Maps filenames to database tables
3. Uses SQLAlchemy to create tables if they don't exist
4. Imports data using pandas DataFrames

**Example CSV Data (klienci.csv):**
```csv
id,nazwa,email,kraj,telefon
1,"Firma X","contact@firmax.com","Polska","+48 600 123 456"
2,"Firma Y","support@firmay.com","Niemcy","+49 170 987 654"
```

### 2. Change Data Capture Process
Once data is in PostgreSQL, Debezium captures all changes and publishes them to Kafka.

**CDC Process Flow:**
1. PostgreSQL writes changes to the WAL
2. Debezium connectors read from replication slots
3. Change events are serialized as JSON
4. Events are published to Kafka topics

**Sample CDC Event:**
```json
{
  "schema": {...},
  "payload": {
    "before": null,
    "after": {
      "id": 1,
      "nazwa": "Firma X",
      "email": "contact@firmax.com",
      "kraj": "Polska",
      "telefon": "+48 600 123 456"
    },
    "source": {
      "version": "2.3.4.Final",
      "connector": "postgresql",
      "name": "dbserver1",
      "ts_ms": 1741899497088,
      "snapshot": "first",
      "db": "postgres",
      "schema": "public",
      "table": "klienci",
      "txId": 745,
      "lsn": 24949288
    },
    "op": "r",
    "ts_ms": 1741899497103
  }
}
```

### 3. Spark Stream Processing
Spark continuously processes the CDC events from Kafka and applies transformations.

**Processing Steps:**
1. Read from Kafka topics using Structured Streaming
2. Parse the JSON data and extract the payload
3. Apply transformations and aggregations
4. Write results to MinIO in different formats

**Spark Processing Code Example:**
```python
# Read from Kafka
df_klienci = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "dbserver1.public.klienci") \
    .option("startingOffsets", "earliest") \
    .load()

# Parse JSON and extract data
df_parsed = df_klienci \
    .selectExpr("CAST(value AS STRING)") \
    .select(from_json("value", kafka_schema).alias("data")) \
    .select("data.payload.after.*")

# Aggregate data
df_by_country = df_parsed \
    .groupBy("kraj") \
    .count()

# Write to MinIO
query = df_by_country \
    .writeStream \
    .format("parquet") \
    .option("path", "s3a://processed-data/klienci-by-country") \
    .option("checkpointLocation", "/tmp/checkpoint1") \
    .start()
```

### 4. Data Storage in MinIO
Processed data is stored in MinIO in organized buckets and formats.

**Storage Organization:**
- `/processed-data/raw-kafka-data/`: Raw events from Kafka
- `/processed-data/klienci-by-country/`: Customer aggregations
- `/processed-data/avg-age-by-position/`: Employee statistics

**Accessing Data in MinIO:**
```bash
# List all buckets
docker exec minio mc ls myminio/

# List files in the processed-data bucket
docker exec minio mc ls myminio/processed-data/ --recursive

# Download a specific file
docker exec minio mc cp myminio/processed-data/raw-kafka-data/part-00000-xxx.parquet /tmp/
```

## Monitoring and Management

### Monitoring Components

1. **PostgreSQL Monitoring**
   ```bash
   # Check replication slots
   docker exec postgres_db psql -U postgres -c "SELECT * FROM pg_replication_slots;"
   
   # Check publications
   docker exec postgres_db psql -U postgres -c "SELECT * FROM pg_publication;"
   
   # View table data
   docker exec postgres_db psql -U postgres -c "SELECT * FROM klienci LIMIT 5;"
   ```

2. **Kafka Monitoring**
   ```bash
   # List topics
   docker exec kafka kafka-topics --bootstrap-server kafka:9092 --list
   
   # View messages in a topic
   docker exec kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic dbserver1.public.klienci --from-beginning --max-messages 1
   
   # Check topic details
   docker exec kafka kafka-topics --bootstrap-server kafka:9092 --describe --topic dbserver1.public.klienci
   ```

3. **Debezium Connector Management**
   ```bash
   # List connectors
   curl -s http://localhost:8083/connectors | jq .
   
   # Check connector status
   curl -s http://localhost:8083/connectors/klienci-connector/status | jq .
   
   # Delete a connector
   curl -X DELETE http://localhost:8083/connectors/klienci-connector
   
   # Create a connector
   curl -X POST -H "Content-Type: application/json" -d '{
     "name": "klienci-connector",
     "config": {
       "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
       "database.hostname": "postgres_db",
       "database.port": "5432",
       "database.user": "postgres",
       "database.password": "password",
       "database.dbname": "postgres",
       "database.server.name": "dbserver1",
       "table.include.list": "public.klienci",
       "plugin.name": "pgoutput",
       "topic.prefix": "dbserver1",
       "slot.name": "debezium_klienci",
       "publication.name": "dbz_publication_klienci"
     }
   }' http://localhost:8083/connectors
   ```

4. **Spark Application Monitoring**
   ```bash
   # View Spark logs
   docker logs spark-app
   
   # Access Spark UI
   # Open in browser: http://localhost:8080
   
   # Check Spark jobs
   docker exec spark-master /opt/bitnami/spark/bin/spark-submit --version
   ```

5. **MinIO Monitoring**
   ```bash
   # Configure MinIO client
   docker exec minio mc alias set myminio http://localhost:9000 minio minio123
   
   # List buckets
   docker exec minio mc ls myminio/
   
   # Check bucket size
   docker exec minio mc du myminio/processed-data/
   
   # Access MinIO console
   # Open in browser: http://localhost:9001
   # Login with: minio / minio123
   ```

### Advanced Management Tasks

1. **Adding New Tables to Monitor**
   
   To add a new table to the pipeline:
   
   a. Create the table in PostgreSQL:
   ```sql
   CREATE TABLE kategorie (
     id SERIAL PRIMARY KEY,
     nazwa VARCHAR(100),
     opis TEXT
   );
   ```
   
   b. Create a Debezium connector for the table:
   ```bash
   curl -X POST -H "Content-Type: application/json" -d '{
     "name": "kategorie-connector",
     "config": {
       "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
       "database.hostname": "postgres_db",
       "database.port": "5432",
       "database.user": "postgres",
       "database.password": "password",
       "database.dbname": "postgres",
       "database.server.name": "dbserver1",
       "table.include.list": "public.kategorie",
       "plugin.name": "pgoutput",
       "topic.prefix": "dbserver1",
       "slot.name": "debezium_kategorie",
       "publication.name": "dbz_publication_kategorie"
     }
   }' http://localhost:8083/connectors
   ```
   
   c. Update the Spark processor to include the new topic.

2. **Scaling the Pipeline**
   
   To handle increased load:
   
   a. Add more Kafka brokers:
   ```yaml
   # Add to docker-compose.yml
   kafka2:
     image: confluentinc/cp-kafka:latest
     depends_on:
       - zookeeper
     environment:
       KAFKA_BROKER_ID: 2
       KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
       # ... other settings
   ```
   
   b. Add more Spark workers:
   ```yaml
   # Add to docker-compose.yml
   spark-worker-2:
     image: bitnami/spark:latest
     environment:
       - SPARK_MODE=worker
       - SPARK_MASTER_URL=spark://spark-master:7077
     depends_on:
       - spark-master
   ```

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Debezium Connector Fails to Start

**Symptoms:**
- Connector status shows "FAILED"
- Error mentions "publication already exists"

**Solutions:**
- Check if publication exists:
  ```bash
  docker exec postgres_db psql -U postgres -c "SELECT * FROM pg_publication;"
  ```
- Drop the existing publication:
  ```bash
  docker exec postgres_db psql -U postgres -c "DROP PUBLICATION dbz_publication_klienci;"
  ```
- Recreate the connector with a unique publication name

#### 2. Spark Cannot Read from Kafka Topics

**Symptoms:**
- Spark logs show "UnknownTopicOrPartitionException"
- No data is processed

**Solutions:**
- Verify topic exists:
  ```bash
  docker exec kafka kafka-topics --bootstrap-server kafka:9092 --list
  ```
- Create topics manually if needed:
  ```bash
  docker exec kafka kafka-topics --bootstrap-server kafka:9092 --create --topic dbserver1.public.klienci --partitions 1 --replication-factor 1
  ```
- Check Kafka broker connectivity from Spark container

#### 3. PostgreSQL WAL Level Issues

**Symptoms:**
- Debezium connectors fail with "wal_level property must be logical"
- Replication slots aren't being created

**Solutions:**
- Check current WAL level:
  ```bash
  docker exec postgres_db psql -U postgres -c "SHOW wal_level;"
  ```
- Update WAL level:
  ```bash
  docker exec postgres_db psql -U postgres -c "ALTER SYSTEM SET wal_level = logical;"
  ```
- Restart PostgreSQL to apply changes:
  ```bash
  docker-compose restart postgres_db
  ```

#### 4. MinIO Connection Issues

**Symptoms:**
- Cannot list or access data in MinIO
- Spark writes fail with S3 errors

**Solutions:**
- Check MinIO is running:
  ```bash
  docker ps | grep minio
  ```
- Reset MinIO client alias:
  ```bash
  docker exec minio mc alias set myminio http://localhost:9000 minio minio123
  ```
- Create buckets manually if needed:
  ```bash
  docker exec minio mc mb myminio/processed-data
  ```
- Check bucket permissions

#### 5. Debugging with Pipeline Tool

Use the included debug utility to check all components:
```bash
python debug_pipeline.py --component all
```

For specific components:
```bash
python debug_pipeline.py --component kafka
python debug_pipeline.py --component postgres
python debug_pipeline.py --component debezium
```

### Logging and Diagnostics

Viewing logs for each component:

```bash
# PostgreSQL logs
docker logs postgres_db

# Kafka logs
docker logs kafka

# Debezium logs
docker logs debezium

# Spark application logs
docker logs spark-app

# MinIO logs
docker logs minio
```

## Performance Optimization

### PostgreSQL Optimization

- Increase shared buffers for better caching:
  ```
  shared_buffers = 256MB
  ```
- Optimize WAL settings:
  ```
  wal_buffers = 16MB
  checkpoint_timeout = 10min
  ```

### Kafka Optimization

- Increase partition count for parallelism:
  ```bash
  docker exec kafka kafka-topics --bootstrap-server kafka:9092 --alter --topic dbserver1.public.klienci --partitions 3
  ```
- Tune producer/consumer settings in the application

### Spark Optimization

- Increase memory allocation:
  ```yaml
  spark-worker:
    environment:
      SPARK_WORKER_MEMORY: 2g
  ```
- Optimize executor settings in Spark application:
  ```python
  spark = SparkSession.builder \
      .config("spark.executor.memory", "2g") \
      .config("spark.executor.cores", 2) \
      .getOrCreate()
  ```

## Extending the Pipeline

### Adding Data Transformations

To add new data transformations:

1. Edit `spark-app/spark_processor.py`
2. Add new processing logic:
   ```python
   # Example: Calculate revenue per customer
   df_revenue = df_klienci \
       .join(df_orders, "id") \
       .groupBy("nazwa") \
       .sum("order_value") \
       .withColumnRenamed("sum(order_value)", "total_revenue")
   
   # Write to new location
   query3 = df_revenue \
       .writeStream \
       .outputMode("complete") \
       .format("parquet") \
       .option("checkpointLocation", "/tmp/checkpoint3") \
       .option("path", "s3a://processed-data/customer-revenue") \
       .start()
   ```

### Adding Data Quality Checks

Implement data quality checks in Spark:

```python
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

### Building Dashboards

1. Connect visualization tools to MinIO:
   - Configure Superset, Tableau, or PowerBI with S3 connection
   - Set up credentials for MinIO access
   
2. Create views over processed data:
   - Customer distribution by country
   - Employee age demographics
   - Project timeline visualization