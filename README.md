# Real-time Data Pipeline with Change Data Capture (CDC)

## 📋 Quick Start Guide

```bash
# Clone the repository
git clone <repository-url>
cd <project-directory>

# Start all services with the automated script
./start-and-test-pipeline.sh

# Check pipeline status
python debug_pipeline.py
```

## 🔍 What This Project Does

This project implements a comprehensive real-time data pipeline that:

1. **Captures changes** from a PostgreSQL database in real-time using Change Data Capture (CDC)
2. **Streams them** through Kafka as events
3. **Processes them** with Apache Spark in two stages:
   - Stream processing to capture all events in raw format
   - Batch processing to transform data into business analytics 
4. **Stores results** in MinIO (S3-compatible storage) for downstream applications

The pipeline produces two key analytical outputs:
- Customer distribution by country (`klienci-by-country`)
- Average employee age by position (`avg-age-by-position`)

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

### Component Roles

1. **PostgreSQL**: Source database storing customer (klienci), employee (pracownicy), and project (projekty) data. Configured for logical replication to enable CDC.

2. **Debezium**: Captures database changes from PostgreSQL's Write-Ahead Log (WAL) and publishes them to Kafka topics. Each table is monitored by a separate connector.

3. **Kafka**: Messaging system that stores change events in topics and makes them available to consumers. Managed by Zookeeper for coordination.

4. **Zookeeper**: Manages Kafka cluster state, topic configurations, and helps with leader election in Kafka.

5. **Spark**: Processes data in two stages:
   - **Streaming job**: Continuously reads from Kafka and writes raw events to MinIO
   - **Batch processor**: Periodically reads the raw data and transforms it into business analytics (running in local mode)

6. **MinIO**: S3-compatible object storage that stores:
   - Raw Kafka data (`raw-kafka-data`)
   - Customer count by country (`klienci-by-country`) 
   - Average employee age by position (`avg-age-by-position`)

## 📁 Project Structure

```
├── csv_files/               # Sample data files to be imported
│   ├── klienci.csv          # Customer data 
│   ├── pracownicy.csv       # Employee data
│   └── projekty.csv         # Project data
│
├── spark-app/               # Spark application code
│   ├── Dockerfile           # Spark container configuration
│   ├── entrypoint.sh        # Spark app startup script
│   ├── requirements.txt     # Python dependencies for Spark
│   ├── setup_debezium.py    # Script to configure Debezium
│   ├── setup_minio.py       # Script to setup MinIO buckets
│   ├── spark_processor.py   # Spark streaming job
│   └── batch_processor.py   # Spark batch processing job (running in local mode)
│
├── debug_pipeline.py        # Pipeline troubleshooting utility
├── docker-compose.yml       # Docker services configuration
├── docker-network-diagnostic.sh # Network troubleshooting script
├── Dockerfile               # Main app Dockerfile
├── import_csv_to_postgres.py # CSV to PostgreSQL import script
├── kafka-check.sh           # Kafka health check script
├── pipeline-test.sh         # Pipeline component test script
├── reset-environment.sh     # Script to reset the environment
├── start-and-test-pipeline.sh # Main script to start and test pipeline
├── test_pipeline.sh         # End-to-end pipeline test script
└── other utility scripts    # Various diagnostic and maintenance scripts
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

   Use the main startup script which handles proper initialization and testing:
   ```bash
   ./start-and-test-pipeline.sh
   ```

   The script supports several flags:
   - `--reset` - Completely resets the environment (removes volumes, stops containers)
   - `--debug` - Runs with extra debug information and diagnostic tools
   - `--skip-test` - Skips running the test pipeline after startup

   For example, to reset the environment and run in debug mode:
   ```bash
   ./start-and-test-pipeline.sh --reset --debug
   ```

3. **Verify the setup**
   ```bash
   # Check if all containers are running
   docker-compose ps
   
   # Run the debugging utility to check component status
   python debug_pipeline.py
   ```

## 💡 Data Flow and Transformations

### Step 1: Data Import from CSV to PostgreSQL

The `csv_import_app` container reads CSV files from the `csv_files` directory and imports them into PostgreSQL tables:

- **klienci** (customers): 
  - id: Integer
  - nazwa: String (company name)
  - email: String
  - kraj: String (country)
  - telefon: String (phone)

- **pracownicy** (employees): 
  - id: Integer
  - imie: String (first name)
  - nazwisko: String (last name)
  - email: String
  - wiek: Integer (age)
  - stanowisko: String (position)

- **projekty** (projects): 
  - id: Integer
  - nazwa: String (name)
  - opis: String (description)
  - data_rozpoczecia: String (start date)
  - data_zakonczenia: String (end date)

### Step 2: Change Data Capture with Debezium

Debezium connectors monitor PostgreSQL's transaction log and capture changes in real-time:

- Each table has a dedicated Debezium connector configured in `setup_debezium.py`
- When data changes in PostgreSQL, Debezium creates events in JSON format
- Events contain both the previous state (`before`) and new state (`after`) of the record
- Debezium publishes these events to Kafka topics named `dbserver1.public.<table_name>`

### Step 3: Kafka Message Streaming

Kafka maintains three separate topics for the database tables:
- `dbserver1.public.klienci` - Customer change events
- `dbserver1.public.pracownicy` - Employee change events
- `dbserver1.public.projekty` - Project change events

Each message contains the complete record data plus metadata about the change (create, update, delete).

### Step 4: Two-Stage Spark Processing

#### Stream Processing Stage (`spark_processor.py`)
- Reads events continuously from all Kafka topics
- Preserves all events including their timestamp, topic, and JSON payload
- Writes raw data to MinIO in the `raw-kafka-data` folder
- Maintains exactly-once processing with checkpointing

#### Batch Processing Stage (`batch_processor.py`)
Performs two specific analytical transformations:

1. **Customer Distribution by Country**:
   - Reads raw JSON events from `raw-kafka-data`
   - Filters for customer (klienci) data
   - Extracts country ("kraj") field from JSON
   - Groups by country and counts customers in each country
   - Stores results in `klienci-by-country` folder in MinIO

2. **Average Age by Position**:
   - Reads raw JSON events from `raw-kafka-data`
   - Filters for employee (pracownicy) data
   - Extracts position ("stanowisko") and age ("wiek") fields from JSON
   - Calculates average age for each position
   - Stores results in `avg-age-by-position` folder in MinIO

### Step 5: Data Storage in MinIO

When the pipeline works correctly, the following data should appear in MinIO:

- **processed-data** (bucket)
  - **raw-kafka-data** - Contains raw Kafka events in Parquet format
    - `part-XXXXX-*.snappy.parquet` files - The actual data files
    - `_spark_metadata` - Metadata directory for streaming checkpoints
  - **klienci-by-country** - Contains customer analysis in Parquet format
    - `part-XXXXX-*.snappy.parquet` files - Data files with country counts
    - `_SUCCESS` - Marker file indicating successful write
  - **avg-age-by-position** - Contains employee analysis in Parquet format
    - `part-XXXXX-*.snappy.parquet` files - Data files with position-age averages
    - `_SUCCESS` - Marker file indicating successful write
  - **test-data** - Contains test data files generated during startup

## 🧰 Common Problems and Solutions

During the development of this pipeline, several issues were encountered and resolved:

1. **DNS and Network Connectivity Issues**:
   - **Problem**: Containers couldn't reliably resolve hostnames of other containers.
   - **Solution**: Added static IP entries to `/etc/hosts` and extended DNS TTL settings in the JVM.

2. **Kafka Topic Availability Timing**:
   - **Problem**: Spark streaming job started before Kafka topics were fully created by Debezium.
   - **Solution**: Enhanced `entrypoint.sh` with proper wait mechanism for topic creation and leader election.

3. **Spark Worker Resource Allocation**:
   - **Problem**: Batch processing jobs couldn't acquire resources from the Spark cluster.
   - **Solution**: Changed batch processor to run in local mode (`master("local[*]")`) instead of cluster mode.

4. **Data Serialization Issues**:
   - **Problem**: Binary data in Parquet files wasn't properly interpreted.
   - **Solution**: Added `spark.sql.parquet.binaryAsString=true` configuration.

5. **Container Startup Order Dependencies**:
   - **Problem**: Services had subtle dependencies on each other's initialization.
   - **Solution**: Created sequenced startup with appropriate delays in `start-and-test-pipeline.sh`.

These improvements make the pipeline more resilient to timing issues and distributed system challenges.

## 🔧 Verifying Pipeline Operation

### Checking Pipeline Components

Use the `debug_pipeline.py` script to check all components:

```bash
# Check all components
python debug_pipeline.py

# Check specific components
python debug_pipeline.py --component postgres  # Database and tables
python debug_pipeline.py --component kafka     # Message broker topics
python debug_pipeline.py --component debezium  # CDC connectors
python debug_pipeline.py --component spark     # Processing jobs
python debug_pipeline.py --component minio     # Output storage
```

### Verifying Data in MinIO

Check if the analysis results are available in MinIO:

```bash
# List all contents recursively
docker exec minio mc ls myminio/processed-data/ --recursive

# Check raw Kafka data
docker exec minio mc ls myminio/processed-data/raw-kafka-data/ --recursive

# Check customer country distribution analysis
docker exec minio mc ls myminio/processed-data/klienci-by-country/ --recursive

# Check average age by position analysis 
docker exec minio mc ls myminio/processed-data/avg-age-by-position/ --recursive
```

If the `klienci-by-country` and `avg-age-by-position` directories have data (especially `.parquet` files), your pipeline is working correctly.