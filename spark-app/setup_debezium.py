import requests
import json
import time

def setup_debezium_connector():
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
        except Exception:
            pass
        
        print(f"Waiting for Debezium to be ready... Retry {retries+1}/{max_retries}")
        retries += 1
        time.sleep(5)
    
    if retries == max_retries:
        print("Failed to connect to Debezium")
        return

    # Konfiguracja konektora dla tabeli "klienci" z unikalnym replication slot
    klienci_connector = {
        "name": "klienci-connector",
        "config": {
            "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
            "database.hostname": "db",
            "database.port": "5432",
            "database.user": "postgres",
            "database.password": "password",
            "database.dbname": "postgres",
            "database.server.name": "dbserver1",
            "table.include.list": "public.klienci",
            "plugin.name": "pgoutput",
            "topic.prefix": "dbserver1",
            "slot.name": "debezium_klienci"
        }
    }
    
    # Konfiguracja konektora dla tabeli "pracownicy" z unikalnym replication slot
    pracownicy_connector = {
        "name": "pracownicy-connector",
        "config": {
            "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
            "database.hostname": "db",
            "database.port": "5432",
            "database.user": "postgres",
            "database.password": "password",
            "database.dbname": "postgres",
            "database.server.name": "dbserver1",
            "table.include.list": "public.pracownicy",
            "plugin.name": "pgoutput",
            "topic.prefix": "dbserver1",
            "slot.name": "debezium_pracownicy"
        }
    }
    
    # Konfiguracja konektora dla tabeli "projekty" z unikalnym replication slot
    projekty_connector = {
        "name": "projekty-connector",
        "config": {
            "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
            "database.hostname": "db",
            "database.port": "5432",
            "database.user": "postgres",
            "database.password": "password",
            "database.dbname": "postgres",
            "database.server.name": "dbserver1",
            "table.include.list": "public.projekty",
            "plugin.name": "pgoutput",
            "topic.prefix": "dbserver1",
            "slot.name": "debezium_projekty"
        }
    }
    
    # Rejestracja konektorów
    for connector in [klienci_connector, pracownicy_connector, projekty_connector]:
        try:
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
        except Exception as e:
            print(f"Error registering connector {connector['name']}: {str(e)}")

if __name__ == "__main__":
    setup_debezium_connector()
