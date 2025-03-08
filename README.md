# Import CSV do PostgreSQL za pomocą SQLAlchemy i Dockera

Ten skrypt Python importuje pliki CSV do bazy danych PostgreSQL. Każdy plik CSV w podanym folderze jest zapisywany jako osobna tabela w bazie danych. Jeśli w folderze znajdują się pliki o podobnych nazwach (np. `klienci.csv` i `klienci2.csv`), ich zawartość zostanie połączona i zapisania do tej samej tabeli.

## Wymagania
- Python 3
- Docker + Docker Compose
- PostgreSQL
- Zainstalowane biblioteki Python (jeśli uruchamiasz lokalnie):
  ```bash
  pip install pandas sqlalchemy psycopg2-binary
  ```

## Instalacja i konfiguracja

### Uruchomienie lokalne (bez Dockera)
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

4. **Uruchom skrypt:**
   ```bash
   python import_csv_to_postgres.py --folder csv_files --db_user postgres --db_password secret --db_host 127.0.0.1 --db_port 5432 --db_name mydb
   ```

---
### Uruchomienie w Dockerze

1. **Zbuduj i uruchom kontenery:**
   ```bash
   docker-compose up --build
   ```

2. **(Opcjonalnie) Zatrzymaj kontenery:**
   ```bash
   docker-compose down
   ```

---
## Struktura projektu
```
├── csv_files/               # Folder z plikami CSV
├── import_csv_to_postgres.py # Główny skrypt do importu danych
├── Dockerfile               # Konfiguracja Dockera
├── docker-compose.yml       # Konfiguracja Docker Compose
├── requirements.txt         # Lista zależności
├── .env                     # Plik z ustawieniami bazy danych (opcjonalnie)
└── README.md                # Dokumentacja
```

## Jak działa skrypt?
1. Pobiera listę plików `.csv` z folderu podanego w `--folder`.
2. Wczytuje każdy plik do Pandas DataFrame.
3. Jeśli kilka plików ma tę samą nazwę (z numerami, np. `klienci.csv` i `klienci2.csv`), dane są łączone do jednej tabeli.
4. Tworzy tabelę o nazwie zgodnej z nazwą pliku (jeśli nie istnieje, dodaje nowe dane do istniejącej tabeli).
5. Importuje dane do PostgreSQL.

## Przykład struktury plików CSV
### `pracownicy.csv`
```
id,imie,nazwisko,email,wiek,stanowisko
1,Jan Kowalski,jan.kowalski@example.com,30,Inżynier
2,Anna Nowak,anna.nowak@example.com,25,Analityk
```

### `klienci.csv`
```
id,nazwa,email,kraj,telefon
1,Firma X,contact@firmax.com,Polska,+48 600 123 456
2,Firma Y,support@firmay.com,Niemcy,+49 170 987 654
```

### `klienci2.csv`
```
id,nazwa,email,kraj,telefon
3,TechNova,contact@technova.io,USA,+1 650 555 0199
4,Innovate Solutions,info@innovatesol.eu,Holandia,+31 20 123 4567
5,GreenTech,office@greentech.de,Niemcy,+49 30 789 6543
```

Po załadowaniu obydwu plików do bazy danych, tabela `klienci` zawierać będzie dane zarówno z `klienci.csv`, jak i `klienci2.csv`.

## Obsługa błędów
- Jeśli folder nie istnieje, skrypt zgłosi błąd.
- Jeśli plik CSV jest pusty lub nieprawidłowy, skrypt go pominie.
- Jeśli tabela już istnieje, nowe dane zostaną do niej dodane (`if_exists='append'`).

## Licencja
MIT License
