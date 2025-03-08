# Import CSV do PostgreSQL za pomocą SQLAlchemy

Ten skrypt Python importuje pliki CSV do bazy danych PostgreSQL. Każdy plik CSV w podanym folderze jest zapisywany jako osobna tabela w bazie danych. Nazwa tabeli odpowiada nazwie pliku (bez rozszerzenia `.csv`).

## Wymagania
- Python 3
- PostgreSQL
- Zainstalowane biblioteki Python:
  ```bash
  pip install pandas sqlalchemy psycopg2-binary
  ```

## Instalacja i konfiguracja
1. **Utwórz wirtualne środowisko (opcjonalnie):**
   ```bash
   python3 -m venv env
   source env/bin/activate  # Linux/MacOS
   env\Scripts\activate  # Windows
   ```

2. **Zainstaluj wymagane pakiety:**
   ```bash
   pip install pandas sqlalchemy psycopg2-binary
   ```

3. **Przygotuj pliki CSV:**
   - Utwórz folder `csv_files`.
   - Umieść tam pliki `.csv`.

## Uruchamianie skryptu

```bash
python import_csv_to_postgres.py --folder csv_files \
  --db_user postgres --db_password secret \
  --db_host 127.0.0.1 --db_port 5432 --db_name mydb
```

### Argumenty:
- `--folder` – ścieżka do folderu z plikami CSV (wymagane).
- `--db_user` – użytkownik PostgreSQL (domyślnie: `postgres`).
- `--db_password` – hasło do bazy danych (domyślnie: `password`).
- `--db_host` – adres hosta PostgreSQL (domyślnie: `localhost`).
- `--db_port` – port PostgreSQL (domyślnie: `5432`).
- `--db_name` – nazwa bazy danych (domyślnie: `postgres`).

## Jak działa skrypt?
1. Pobiera listę plików `.csv` z folderu podanego w `--folder`.
2. Wczytuje każdy plik do Pandas DataFrame.
3. Tworzy tabelę o nazwie zgodnej z nazwą pliku (jeśli nie istnieje, zastępuje ją).
4. Importuje dane do PostgreSQL.

## Przykład struktury plików CSV
### `pracownicy.csv`
```
id,imie,nazwisko,email,wiek,stanowisko
1,Jan,Kowalski,jan.kowalski@example.com,30,Inżynier
2,Anna,Nowak,anna.nowak@example.com,25,Analityk
```

### `projekty.csv`
```
id,nazwa,opis,data_rozpoczecia,data_zakonczenia
1,System CRM,Zarządzanie relacjami,2023-01-10,2023-06-30
```

## Obsługa błędów
- Jeśli folder nie istnieje, skrypt zgłosi błąd.
- Jeśli plik CSV jest pusty lub nieprawidłowy, skrypt go pominie.
- Jeśli tabela już istnieje, zostanie zastąpiona (`if_exists='replace'`).

## Licencja
MIT License

