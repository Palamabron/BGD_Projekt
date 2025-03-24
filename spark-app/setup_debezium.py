import requests
import json
import time
import socket

def setup_debezium_connector():
    # Try to resolve the Kafka hostname to diagnose network issues
    try:
        kafka_ip = socket.gethostbyname("kafka")
        print(f"Successfully resolved kafka to IP: {kafka_ip}")
    except socket.gaierror:
        print("WARNING: Unable to resolve 'kafka' hostname from Debezium container")
    
    # Use container name instead of localhost
    debezium_url = "http://debezium:8083"
    max_retries = 30
    retries = 0

    # Oczekiwanie na dostępność Debezium Connect REST API
    while retries < max_retries:
        try:
            response = requests.get(f"{debezium_url}/connectors")
            if response.status_code == 200:
                print("Debezium is ready")
                break
        except Exception as e:
            print(f"Exception connecting to Debezium: {str(e)}")
        
        print(f"Waiting for Debezium to be ready... Retry {retries+1}/{max_retries}")
        retries += 1
        time.sleep(5)
    
    if retries == max_retries:
        print("Failed to connect to Debezium")
        return

    # First, delete any existing connectors to avoid conflicts
    try:
        response = requests.get(f"{debezium_url}/connectors")
        if response.status_code == 200:
            existing_connectors = response.json()
            for connector in existing_connectors:
                print(f"Deleting existing connector: {connector}")
                requests.delete(f"{debezium_url}/connectors/{connector}")
                time.sleep(2)  # Give some time between deletions
    except Exception as e:
        print(f"Error deleting existing connectors: {str(e)}")

    # Konfiguracja konektora dla tabeli "klienci" z unikalnym replication slot i publication
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
            "table.include.list": "public.klienci",
            "plugin.name": "pgoutput",
            "topic.prefix": "dbserver1",
            "slot.name": "debezium_klienci",
            "publication.name": "dbz_publication_klienci"  # Unique publication name
        }
    }
    
    # Konfiguracja konektora dla tabeli "pracownicy" z unikalnym replication slot i publication
    pracownicy_connector = {
        "name": "pracownicy-connector",
        "config": {
            "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
            "database.hostname": "postgres_db",
            "database.port": "5432",
            "database.user": "postgres",
            "database.password": "password",
            "database.dbname": "postgres",
            "database.server.name": "dbserver1",
            "table.include.list": "public.pracownicy",
            "plugin.name": "pgoutput",
            "topic.prefix": "dbserver1",
            "slot.name": "debezium_pracownicy",
            "publication.name": "dbz_publication_pracownicy"  # Unique publication name
        }
    }
    
    # Konfiguracja konektora dla tabeli "projekty" z unikalnym replication slot i publication
    projekty_connector = {
        "name": "projekty-connector",
        "config": {
            "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
            "database.hostname": "postgres_db",
            "database.port": "5432",
            "database.user": "postgres",
            "database.password": "password",
            "database.dbname": "postgres",
            "database.server.name": "dbserver1",
            "table.include.list": "public.projekty",
            "plugin.name": "pgoutput",
            "topic.prefix": "dbserver1",
            "slot.name": "debezium_projekty",
            "publication.name": "dbz_publication_projekty"  # Unique publication name
        }
    }
    
    # Rejestracja konektorów
    for connector in [klienci_connector, pracownicy_connector, projekty_connector]:
        try:
            print(f"Registering connector: {connector['name']}")
            response = requests.post(
                f"{debezium_url}/connectors",
                headers={"Content-Type": "application/json"},
                data=json.dumps(connector)
            )
            if response.status_code in [200, 201]:
                print(f"Successfully registered connector: {connector['name']}")
            else:
                print(f"Failed to register connector: {connector['name']}")
                print(f"Response: {response.status_code} - {response.text}")
            
            # Wait a bit between connector registrations to avoid race conditions
            time.sleep(5)
        except Exception as e:
            print(f"Error registering connector {connector['name']}: {str(e)}")

if __name__ == "__main__":
    setup_debezium_connector()