# Kompleksowy Pipeline Danych z CSV do Data Lake

Ten projekt implementuje pełny pipeline danych, który importuje pliki CSV do bazy PostgreSQL, monitoruje zmiany w bazie przy użyciu Debezium, przetwarza dane strumieniowo w Apache Spark oraz zapisuje wyniki w MinIO (kompatybilnym z S3).

## Architektura

System składa się z następujących komponentów:
- **PostgreSQL** – baza danych do przechowywania danych z plików CSV.
- **Python App** – aplikacja importująca pliki CSV do bazy danych.
- **Kafka & Zookeeper** – system komunikacji asynchronicznej.
- **Debezium** – narzędzie do przechwytywania zmian w bazie danych (CDC).  
  *Uwaga:* Każdy konektor Debezium używa unikalnej nazwy replication slot, co zapobiega konfliktom.
- **Apache Spark** – silnik do przetwarzania danych strumieniowych.  
  Wprowadzono modyfikacje konfiguracji źródeł Kafka, takie jak ustawienie opcji `startingOffsets` oraz `failOnDataLoss`. Dodano także opóźnienie startu zapytań, aby dać brokerowi Kafka czas na utworzenie i propagację tematów.
- **MinIO** – magazyn danych kompatybilny z S3, do którego zapisywane są wyniki przetwarzania (w formacie Parquet).

## Wymagania
- Docker
- Docker Compose

## Struktura projektu

```
├── csv_files/               # Folder z plikami CSV
├── spark-app/               # Aplikacja Spark do przetwarzania danych
│   ├── Dockerfile           # Konfiguracja Dockera dla Spark
│   ├── entrypoint.sh        # Skrypt startowy
│   ├── requirements.txt     # Zależności Pythona dla Spark
│   ├── setup_debezium.py    # Konfiguracja konektorów Debezium (używają unikalnych replication slotów)
│   ├── setup_minio.py       # Konfiguracja MinIO
│   └── spark_processor.py   # Kod przetwarzania danych w Spark (z konfiguracją źródeł Kafka)
├── import_csv_to_postgres.py # Główny skrypt do importu danych CSV do PostgreSQL
├── Dockerfile               # Konfiguracja Dockera (główny)
├── docker-compose.yml       # Konfiguracja Docker Compose dla całego pipeline
├── requirements.txt         # Lista zależności dla aplikacji
├── .env                     # Plik z ustawieniami bazy danych
└── README.md                # Dokumentacja projektu (to plik)
```

## Uruchomienie

1. **Przygotuj pliki CSV**  
   Umieść pliki CSV w folderze `csv_files`.

2. **Uruchom system**  
   W terminalu w katalogu głównym projektu:
   ```bash
   docker-compose up --build
   ```

## Wprowadzone zmiany i konfiguracja

### Debezium
- **Unikalne replication sloty:**  
  W pliku `setup_debezium.py` każdy konektor (dla tabel: klienci, pracownicy, projekty) używa teraz unikalnej nazwy slotu:
  - "debezium_klienci"
  - "debezium_pracownicy"
  - "debezium_projekty"
  
  Dzięki temu unika się konfliktów wynikających z próby użycia domyślnego slotu "debezium".

### Kafka
- **Auto-create topics:**  
  W docker-compose.yml dla usługi Kafka ustawiono zmienną:
  ```yaml
  KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
  ```
  Dzięki temu tematy (m.in. `dbserver1.public.klienci`, `dbserver1.public.pracownicy`, `dbserver1.public.projekty`) są tworzone automatycznie, gdy aplikacja Kafka Connect lub Spark próbują z nich korzystać.

### Apache Spark
- **Konfiguracja źródeł Kafka:**  
  W pliku `spark_processor.py` dla każdego strumienia Kafka (klienci, pracownicy, projekty) dodano:
  - Opcję `startingOffsets` ustawioną na "earliest", aby konsument pobierał najnowsze metadane.
  - Opcję `failOnDataLoss` ustawioną na "false", by nie przerywać pracy w przypadku utraty danych.
- **Watermark i agregacje:**  
  Dla strumieni "klienci" i "pracownicy" dodano watermark na kolumnie "timestamp" (1 minuta). Agregacje (grupowanie z użyciem funkcji window) są wykonywane z udziałem kolumny czasu, co umożliwia Sparkowi zwolnienie stanu (w trybie append).
- **Opóźnienie startu zapytań:**  
  Przed uruchomieniem zapytań writeStream w `spark_processor.py` dodano opóźnienie (time.sleep(60)). Dzięki temu broker Kafka ma czas na utworzenie tematów i propagację metadanych zanim Spark rozpocznie odczyt.

### MinIO
- **Konfiguracja MinIO:**  
  W pliku `setup_minio.py` wykonuje się test połączenia i tworzenie bucketa `processed-data`. Dane wynikowe zapisywane są w MinIO w formacie Parquet.

## Przepływ Danych

1. **Import CSV do PostgreSQL**  
   Skrypt `import_csv_to_postgres.py` importuje pliki CSV z folderu `csv_files` do bazy PostgreSQL. Podobne pliki (np. `klienci.csv` i `klienci2.csv`) są łączone w jedną tabelę.

2. **Przechwytywanie zmian przez Debezium**  
   Debezium monitoruje zmiany w tabelach PostgreSQL i wysyła je jako wiadomości do Kafki. Każdy konektor korzysta z unikalnego replication slotu.

3. **Przetwarzanie strumieniowe w Spark**  
   Aplikacja Spark odczytuje dane z Kafki, stosuje agregacje (np. liczenie klientów wg kraju, średni wiek wg stanowiska) z wykorzystaniem window i watermark, a następnie zapisuje wyniki do MinIO.

4. **Zapis wyników do MinIO**  
   Wyniki agregacji są zapisywane w formacie Parquet w buckecie `processed-data`. Dane te są dostępne poprzez interfejs S3 MinIO.

## Dostęp do Usług

- **PostgreSQL:** localhost:5432  
- **Kafka:** localhost:9092  
- **Debezium Connect:** localhost:8083  
- **Spark Master UI:** localhost:8080  
- **MinIO Console:** http://localhost:9001 (użytkownik: `minio`, hasło: `minio123`)

## Testowanie Pipeline

Aby upewnić się, że cały pipeline działa:
1. Sprawdź logi kontenerów (csv_import_app, postgres_db, debezium, kafka, spark-app, minio).
2. Zaloguj się do bazy PostgreSQL, aby sprawdzić, czy dane są poprawnie importowane.
3. Użyj narzędzia kafkacat (np. `docker run --rm -it edenhill/kafkacat -b localhost:9092 -L` lub kafkacat z hosta), aby zweryfikować, że tematy istnieją.
4. Zaloguj się do konsoli MinIO (http://localhost:9001) i sprawdź, czy w buckecie `processed-data` pojawiły się wyniki przetwarzania (pliki Parquet).