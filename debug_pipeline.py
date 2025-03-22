#!/usr/bin/env python3
"""
Pipeline Debugging Utility

This script provides utilities to check the status of each component
in the data pipeline and diagnose common issues.
"""

import argparse
import os
import sys
import subprocess
import json
import requests
from tabulate import tabulate
import psycopg2
import boto3
from botocore.client import Config
from kafka import KafkaConsumer, KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError, NoBrokersAvailable

def check_docker_services():
    """Check the status of Docker services"""
    print("\n=== Checking Docker Services ===")
    
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
        
        print(tabulate(services, headers=["Service", "Status", "Health"]))
        
        # Check for stopped services
        stopped_services = [s[0] for s in services if s[1] == "Stopped"]
        if stopped_services:
            print(f"\nWARNING: The following services are not running: {', '.join(stopped_services)}")
            print("You can check their logs with: docker-compose logs <service_name>")
        
    except subprocess.CalledProcessError as e:
        print(f"Error checking Docker services: {e}")
        return False
    
    return True

def check_postgres_db(host="localhost", port=5432, user="postgres", password="password", dbname="postgres"):
    """Check PostgreSQL database connectivity and table contents"""
    print("\n=== Checking PostgreSQL Database ===")
    
    try:
        # Connect to the database
        print(f"Connecting to PostgreSQL: {host}:{port}/{dbname} as {user}...")
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname
        )
        
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public'
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            print("No tables found in the database.")
            return False
        
        print(f"Found {len(tables)} tables: {', '.join(tables)}")
        
        # Check table contents
        table_counts = []
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            count = cursor.fetchone()[0]
            table_counts.append([table, count])
        
        print("\nTable record counts:")
        print(tabulate(table_counts, headers=["Table", "Record Count"]))
        
        # Check replication slots
        cursor.execute("""
            SELECT slot_name, plugin, active 
            FROM pg_replication_slots
        """)
        
        slots = cursor.fetchall()
        
        if slots:
            print("\nReplication slots:")
            slots_table = [[slot[0], slot[1], "Active" if slot[2] else "Inactive"] for slot in slots]
            print(tabulate(slots_table, headers=["Slot Name", "Plugin", "Status"]))
        else:
            print("\nNo replication slots found.")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return False
    
    return True

def check_kafka(bootstrap_servers="localhost:9092"):
    """Check Kafka broker and topics"""
    print("\n=== Checking Kafka Broker ===")
    
    try:
        # Create admin client
        print(f"Connecting to Kafka broker: {bootstrap_servers}...")
        admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
        
        # Check topics
        topics = admin_client.list_topics()
        
        if not topics:
            print("No topics found in Kafka.")
            return False
        
        print(f"Found {len(topics)} topics:")
        print(", ".join(topics))
        
        # Check specific topics
        debezium_topics = [t for t in topics if t.startswith("dbserver1.public")]
        
        if debezium_topics:
            print("\nDebezium CDC topics:")
            for topic in debezium_topics:
                print(f"  - {topic}")
                
                # Try to get messages
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
                        print(f"    • Contains {message_count} messages")
                        # Print first message sample
                        if message_count > 0:
                            first_msg = messages[0].value.decode('utf-8')
                            print(f"    • Sample message (truncated): {first_msg[:200]}...")
                    else:
                        print("    • No messages found")
                    
                    consumer.close()
                
                except Exception as e:
                    print(f"    • Error reading messages: {e}")
        
        admin_client.close()
        
    except NoBrokersAvailable:
        print("Error: Could not connect to Kafka broker")
        return False
    except Exception as e:
        print(f"Error checking Kafka: {e}")
        return False
    
    return True

def check_debezium(host="localhost", port=8083):
    """Check Debezium Connect status and connectors"""
    print("\n=== Checking Debezium Connect ===")
    
    try:
        # Check if Debezium is running
        print(f"Connecting to Debezium Connect: http://{host}:{port}...")
        response = requests.get(f"http://{host}:{port}/connectors")
        
        if response.status_code != 200:
            print(f"Error: Debezium Connect returned status code {response.status_code}")
            return False
        
        connectors = response.json()
        
        if not connectors:
            print("No connectors found in Debezium Connect.")
            return False
        
        print(f"Found {len(connectors)} connectors: {', '.join(connectors)}")
        
        # Check connector status
        connector_status = []
        
        for connector in connectors:
            try:
                status_response = requests.get(f"http://{host}:{port}/connectors/{connector}/status")
                
                if status_response.status_code == 200:
                    status_json = status_response.json()
                    connector_state = status_json.get("connector", {}).get("state", "UNKNOWN")
                    tasks = status_json.get("tasks", [])
                    task_states = [task.get("state", "UNKNOWN") for task in tasks]
                    
                    # Check if there are failed tasks
                    failed_tasks = [i for i, state in enumerate(task_states) if state == "FAILED"]
                    
                    if failed_tasks:
                        # Get error information for failed tasks
                        for task_id in failed_tasks:
                            trace_response = requests.get(f"http://{host}:{port}/connectors/{connector}/tasks/{task_id}/status")
                            if trace_response.status_code == 200:
                                trace_json = trace_response.json()
                                trace = trace_json.get("trace", "No trace available")
                                print(f"\nError in connector {connector}, task {task_id}:")
                                print(trace[:500] + "..." if len(trace) > 500 else trace)
                    
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
        
        print("\nConnector Status:")
        print(tabulate(connector_status, headers=["Connector", "State", "Tasks", "Failed Tasks"]))
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Debezium Connect")
        return False
    except Exception as e:
        print(f"Error checking Debezium Connect: {e}")
        return False
    
    return True

def check_spark(host="localhost", port=8080):
    """Check Spark Master and running applications"""
    print("\n=== Checking Apache Spark ===")
    
    try:
        # Check if Spark Master is running
        print(f"Connecting to Spark Master: http://{host}:{port}...")
        response = requests.get(f"http://{host}:{port}/json/")
        
        if response.status_code != 200:
            print(f"Error: Spark Master returned status code {response.status_code}")
            return False
        
        status_json = response.json()
        
        # Print Spark cluster info
        workers = status_json.get("workers", [])
        apps = status_json.get("activeapps", [])
        
        print(f"Spark Master Status: {status_json.get('status', 'UNKNOWN')}")
        print(f"Workers: {len(workers)}")
        print(f"Running Applications: {len(apps)}")
        
        # Print worker details
        if workers:
            worker_table = [
                [
                    w.get("id", "?"),
                    w.get("state", "UNKNOWN"),
                    f"{w.get('cores', 0)} cores",
                    f"{w.get('memory', 0)} MB"
                ] for w in workers
            ]
            
            print("\nWorkers:")
            print(tabulate(worker_table, headers=["Worker ID", "State", "Cores", "Memory"]))
        
        # Print application details
        if apps:
            app_table = [
                [
                    a.get("id", "?"),
                    a.get("name", "?"),
                    a.get("state", "UNKNOWN"),
                    a.get("cores", 0),
                    a.get("memoryperslave", 0),
                    a.get("starttime", "?")
                ] for a in apps
            ]
            
            print("\nRunning Applications:")
            print(tabulate(app_table, headers=["App ID", "Name", "State", "Cores", "Memory", "Start Time"]))
        else:
            print("\nNo Spark applications are running.")
            print("This could indicate an issue with the Spark job submission or the job has completed.")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Spark Master")
        return False
    except Exception as e:
        print(f"Error checking Spark: {e}")
        return False
    
    return True

def check_minio(endpoint="http://localhost:9000", access_key="minio", secret_key="minio123"):
    """Check MinIO server and buckets"""
    print("\n=== Checking MinIO Storage ===")
    
    try:
        # Create MinIO client
        print(f"Connecting to MinIO: {endpoint}...")
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )
        
        # List buckets
        response = s3_client.list_buckets()
        buckets = response.get('Buckets', [])
        
        if not buckets:
            print("No buckets found in MinIO.")
            return False
        
        print(f"Found {len(buckets)} buckets:")
        
        for bucket in buckets:
            bucket_name = bucket.get('Name')
            print(f"\n- Bucket: {bucket_name}")
            
            # List objects in bucket
            try:
                objects = s3_client.list_objects_v2(Bucket=bucket_name)
                contents = objects.get('Contents', [])
                
                if contents:
                    print(f"  Contains {len(contents)} objects:")
                    
                    # Group objects by prefix (folder)
                    prefixes = {}
                    for obj in contents:
                        key = obj.get('Key', '')
                        size = obj.get('Size', 0)
                        
                        # Get prefix (folder)
                        if '/' in key:
                            prefix = key.split('/')[0]
                            if prefix not in prefixes:
                                prefixes[prefix] = {
                                    'count': 0,
                                    'size': 0
                                }
                            prefixes[prefix]['count'] += 1
                            prefixes[prefix]['size'] += size
                        else:
                            print(f"  • {key} ({size} bytes)")
                    
                    # Print folder summaries
                    for prefix, stats in prefixes.items():
                        print(f"  • {prefix}/ - {stats['count']} objects, {stats['size']} bytes total")
                else:
                    print("  Bucket is empty")
            
            except Exception as e:
                print(f"  Error listing objects: {e}")
        
    except Exception as e:
        print(f"Error checking MinIO: {e}")
        return False
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Debug Data Pipeline Components")
    parser.add_argument("--component", choices=["all", "postgres", "kafka", "debezium", "spark", "minio", "docker"],
                        default="all", help="Component to check (default: all)")
    parser.add_argument("--host", default="localhost", help="Host for components (default: localhost)")
    
    args = parser.parse_args()
    
    # Run checks based on component selection
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
    
    print("\n=== Debug Check Complete ===")

if __name__ == "__main__":
    main()