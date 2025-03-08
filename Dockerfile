# Dockerfile dla projektu importującego pliki CSV do PostgreSQL

# Użycie obrazu bazowego z Pythonem
FROM python:3.10

# Ustawienie katalogu roboczego
WORKDIR /app

# Skopiowanie plików projektu
COPY . /app

# Instalacja zależności z wykorzystaniem cache
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir -r requirements.txt

# Ustawienie zmiennych środowiskowych dla bazy danych
ENV DB_USER=postgres \
    DB_PASSWORD=password \
    DB_HOST=localhost \
    DB_PORT=5432 \
    DB_NAME=postgres

# Komenda uruchamiająca skrypt
CMD ["python", "import_csv_to_postgres.py", "--folder", "csv_files"]