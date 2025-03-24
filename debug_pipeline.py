#!/usr/bin/env python3
"""
Pipeline Debugging Utility

This script provides utilities to check the status of each component
in the data pipeline and diagnose common issues.
"""

import argparse
import os
import subprocess
import time
import logging
import requests
import psycopg2
import boto3
from botocore.client import Config
from kafka import KafkaConsumer, KafkaAdminClient
from kafka.errors import NoBrokersAvailable

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def retry_operation(func, retries=3, delay=5, *args, **kwargs):
    """Helper function to retry an operation."""
    for attempt in range(1, retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.warning(f"Attempt {attempt} failed with error: {e}")
            if attempt < retries:
                time.sleep(delay)
            else:
                raise

def check_docker_services():
    """Check the status of Docker services"""
    logging.info("=== Checking Docker Services ===")
    
    try:
        result = subprocess.run(
            ["docker-compose", "ps"],
            capture_output=True,
            text=True,
            check=True
        )
        # Parse the output to get service status
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        services = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 3:
                service_name = parts[0]
                status = "Running" if "Up" in line else "Stopped"
                healthy = "Healthy" if "healthy" in line else "N/A"
                services.append([service_name, status, healthy])
        
        logging.info("Service Status:")
        for s in services:
            logging.info(f" - {s[0]}: {s[1]}, Health: {s[2]}")
        
        stopped_services = [s[0] for s in services if s[1] == "Stopped"]
        if stopped_services:
            logging.warning(f"Following services are not running: {', '.join(stopped_services)}")
            logging.info("Check logs with: docker-compose logs <service_name>")
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Error checking Docker services: {e}")
        return False
    
    return True

def check_postgres_db(host="localhost", port=5432, user="postgres", password="password", dbname="postgres"):
    """Check PostgreSQL database connectivity and table contents"""
    logging.info("=== Checking PostgreSQL Database ===")
    
    try:
        logging.info(f"Connecting to PostgreSQL: {host}:{port}/{dbname} as {user}...")
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname
        )
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            logging.error("No tables found in the database.")
            return False
        
        logging.info(f"Found {len(tables)} tables: {', '.join(tables)}")
        
        table_counts = []
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            count = cursor.fetchone()[0]
            table_counts.append([table, count])
        
        logging.info("Table record counts:")
        for table, count in table_counts:
            logging.info(f" - {table}: {count} records")
        
        cursor.execute("""
            SELECT slot_name, plugin, active 
            FROM pg_replication_slots
        """)
        slots = cursor.fetchall()
        
        if slots:
            logging.info("Replication slots:")
            for slot in slots:
                status = "Active" if slot[2] else "Inactive"
                logging.info(f" - {slot[0]} (Plugin: {slot[1]}): {status}")
        else:
            logging.info("No replication slots found.")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logging.error(f"Error connecting to PostgreSQL: {e}", exc_info=True)
        return False
    
    return True

def check_kafka(bootstrap_servers="localhost:9092"):
    """Check Kafka broker and topics"""
    logging.info("=== Checking Kafka Broker ===")
    
    try:
        logging.info(f"Connecting to Kafka broker: {bootstrap_servers}...")
        admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
        
        topics = admin_client.list_topics()
        if not topics:
            logging.error("No topics found in Kafka.")
            return False
        
        logging.info(f"Found {len(topics)} topics: {', '.join(topics)}")
        
        debezium_topics = [t for t in topics if t.startswith("dbserver1.public")]
        if debezium_topics:
            logging.info("Debezium CDC topics:")
            for topic in debezium_topics:
                logging.info(f"  - {topic}")
                try:
                    consumer = KafkaConsumer(
                        topic,
                        bootstrap_servers=bootstrap_servers,
                        auto_offset_reset='earliest',
                        consumer_timeout_ms=5000,
                        max_poll_records=5
                    )
                    messages = list(consumer)
                    message_count = len(messages)
                    
                    if message_count > 0:
                        logging.info(f"    Contains {message_count} messages")
                        first_msg = messages[0].value.decode('utf-8')
                        logging.info(f"    Sample message (truncated): {first_msg[:200]}...")
                    else:
                        logging.info("    No messages found")
                    
                    consumer.close()
                except Exception as e:
                    logging.error(f"Error reading messages from topic {topic}: {e}")
        
        admin_client.close()
        
    except NoBrokersAvailable:
        logging.error("Error: Could not connect to Kafka broker")
        return False
    except Exception as e:
        logging.error(f"Error checking Kafka: {e}", exc_info=True)
        return False
    
    return True

def check_debezium(host="localhost", port=8083):
    """Check Debezium Connect status and connectors"""
    logging.info("=== Checking Debezium Connect ===")
    
    try:
        url = f"http://{host}:{port}/connectors"
        logging.info(f"Connecting to Debezium Connect: {url}...")
        
        # Retry logic for Debezium connection
        response = retry_operation(requests.get, 3, 5, url)
        
        if response.status_code != 200:
            logging.error(f"Error: Debezium Connect returned status code {response.status_code}")
            return False
        
        connectors = response.json()
        
        if not connectors:
            logging.error("No connectors found in Debezium Connect.")
            return False
        
        logging.info(f"Found {len(connectors)} connectors: {', '.join(connectors)}")
        
        connector_status = []
        for connector in connectors:
            try:
                status_url = f"http://{host}:{port}/connectors/{connector}/status"
                status_response = retry_operation(requests.get, 3, 5, status_url)
                if status_response.status_code == 200:
                    status_json = status_response.json()
                    connector_state = status_json.get("connector", {}).get("state", "UNKNOWN")
                    tasks = status_json.get("tasks", [])
                    task_states = [task.get("state", "UNKNOWN") for task in tasks]
                    failed_tasks = [i for i, state in enumerate(task_states) if state == "FAILED"]
                    
                    if failed_tasks:
                        for task_id in failed_tasks:
                            trace_url = f"http://{host}:{port}/connectors/{connector}/tasks/{task_id}/status"
                            trace_response = retry_operation(requests.get, 3, 5, trace_url)
                            if trace_response.status_code == 200:
                                trace_json = trace_response.json()
                                trace = trace_json.get("trace", "No trace available")
                                logging.error(f"Error in connector {connector}, task {task_id}: {trace[:500]}")
                    
                    connector_status.append([
                        connector,
                        connector_state,
                        ", ".join(task_states),
                        len(failed_tasks)
                    ])
                else:
                    connector_status.append([connector, "ERROR", f"HTTP {status_response.status_code}", "?"])
            except Exception as e:
                connector_status.append([connector, "ERROR", str(e), "?"])
        
        logging.info("Connector Status:")
        for status in connector_status:
            logging.info(f" - {status[0]}: {status[1]}, Tasks: {status[2]}, Failed: {status[3]}")
        
    except requests.exceptions.ConnectionError:
        logging.error("Error: Could not connect to Debezium Connect")
        return False
    except Exception as e:
        logging.error(f"Error checking Debezium Connect: {e}", exc_info=True)
        return False
    
    return True

def check_spark(host="localhost", port=8080):
    """Check Spark Master and running applications"""
    logging.info("=== Checking Apache Spark ===")
    
    try:
        url = f"http://{host}:{port}/json/"
        logging.info(f"Connecting to Spark Master: {url}...")
        response = retry_operation(requests.get, 3, 5, url)
        
        if response.status_code != 200:
            logging.error(f"Error: Spark Master returned status code {response.status_code}")
            return False
        
        status_json = response.json()
        
        workers = status_json.get("workers", [])
        apps = status_json.get("activeapps", [])
        
        logging.info(f"Spark Master Status: {status_json.get('status', 'UNKNOWN')}")
        logging.info(f"Workers: {len(workers)}")
        logging.info(f"Running Applications: {len(apps)}")
        
        if workers:
            for w in workers:
                logging.info(f"Worker {w.get('id', '?')}: State {w.get('state', 'UNKNOWN')}, Cores: {w.get('cores', 0)}, Memory: {w.get('memory', 0)} MB")
        
        if apps:
            for a in apps:
                logging.info(f"App {a.get('id', '?')}: {a.get('name', '?')}, State: {a.get('state', 'UNKNOWN')}, Cores: {a.get('cores', 0)}, Memory: {a.get('memoryperslave', 0)} MB, Start Time: {a.get('starttime', '?')}")
        else:
            logging.warning("No Spark applications are running. This may indicate an issue with job submission or completed jobs.")
        
    except requests.exceptions.ConnectionError:
        logging.error("Error: Could not connect to Spark Master")
        return False
    except Exception as e:
        logging.error(f"Error checking Spark: {e}", exc_info=True)
        return False
    
    return True

def check_minio(endpoint="http://localhost:9000", access_key="minio", secret_key="minio123"):
    """Check MinIO server and buckets"""
    logging.info("=== Checking MinIO Storage ===")
    
    try:
        logging.info(f"Connecting to MinIO: {endpoint}...")
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )
        response = s3_client.list_buckets()
        buckets = response.get('Buckets', [])
        
        if not buckets:
            logging.error("No buckets found in MinIO.")
            return False
        
        logging.info(f"Found {len(buckets)} buckets.")
        for bucket in buckets:
            bucket_name = bucket.get('Name')
            logging.info(f"Bucket: {bucket_name}")
            try:
                objects = s3_client.list_objects_v2(Bucket=bucket_name)
                contents = objects.get('Contents', [])
                if contents:
                    logging.info(f"  Contains {len(contents)} objects.")
                    prefixes = {}
                    for obj in contents:
                        key = obj.get('Key', '')
                        size = obj.get('Size', 0)
                        if '/' in key:
                            prefix = key.split('/')[0]
                            if prefix not in prefixes:
                                prefixes[prefix] = {'count': 0, 'size': 0}
                            prefixes[prefix]['count'] += 1
                            prefixes[prefix]['size'] += size
                        else:
                            logging.info(f"  - {key} ({size} bytes)")
                    for prefix, stats in prefixes.items():
                        logging.info(f"  - {prefix}/: {stats['count']} objects, {stats['size']} bytes total")
                else:
                    logging.info("  Bucket is empty")
            except Exception as e:
                logging.error(f"Error listing objects in bucket {bucket_name}: {e}")
        
    except Exception as e:
        logging.error(f"Error checking MinIO: {e}", exc_info=True)
        return False
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Debug Data Pipeline Components")
    parser.add_argument("--component", choices=["all", "postgres", "kafka", "debezium", "spark", "minio", "docker"],
                        default="all", help="Component to check (default: all)")
    parser.add_argument("--host", default="localhost", help="Host for components (default: localhost)")
    
    args = parser.parse_args()
    
    if args.component in ["all", "docker"]:
        check_docker_services()
    
    if args.component in ["all", "postgres"]:
        check_postgres_db(host=args.host)
    
    if args.component in ["all", "kafka"]:
        check_kafka(bootstrap_servers=f"{args.host}:9092")
    
    if args.component in ["all", "debezium"]:
        check_debezium(host=args.host)
    
    if args.component in ["all", "spark"]:
        check_spark(host=args.host)
    
    if args.component in ["all", "minio"]:
        check_minio(endpoint=f"http://{args.host}:9000")
    
    logging.info("=== Debug Check Complete ===")

if __name__ == "__main__":
    main()
