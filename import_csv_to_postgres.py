import os
import argparse
import pandas as pd
from sqlalchemy import create_engine

# Funkcja do importowania plików CSV do bazy PostgreSQL

def import_csv_to_postgres(folder, db_user, db_password, db_host, db_port, db_name):
    # Tworzenie URL połączenia zgodnego z SQLAlchemy
    connection_url = f'postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'

    # Utworzenie engine'a SQLAlchemy
    engine = create_engine(connection_url)

    # Sprawdzenie, czy folder istnieje
    if not os.path.exists(folder):
        print(f"Błąd: Folder '{folder}' nie istnieje.")
        return

    # Słownik przechowujący DataFrame dla każdej tabeli
    tables = {}

    # Iteracja po plikach w folderze
    for file in sorted(os.listdir(folder)):
        if file.endswith('.csv'):
            table_name = os.path.splitext(file)[0].rstrip("0123456789")  # Usuwa cyfry z końca nazwy
            file_path = os.path.join(folder, file)

            try:
                # Wczytanie danych z CSV do DataFrame
                df = pd.read_csv(file_path)
                print(f"Wczytywanie pliku '{file_path}' do tabeli '{table_name}'")
                
                # Jeśli tabela już istnieje w słowniku, dodajemy dane do istniejącego DataFrame
                if table_name in tables:
                    tables[table_name] = pd.concat([tables[table_name], df], ignore_index=True)
                else:
                    tables[table_name] = df
            
            except Exception as e:
                print(f"Błąd podczas wczytywania pliku '{file_path}': {e}")

    # Wstawianie danych do bazy
    for table_name, df in tables.items():
        try:
            df.to_sql(table_name, engine, if_exists='append', index=False)
            print(f"Dane dla tabeli '{table_name}' zostały dodane do bazy PostgreSQL.")
        except Exception as e:
            print(f"Błąd podczas zapisu do tabeli '{table_name}': {e}")

    print("Import zakończony.")

# Parsowanie argumentów wiersza poleceń
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import plików CSV do bazy PostgreSQL")
    
    parser.add_argument("--folder", required=True, help="Ścieżka do folderu z plikami CSV")
    parser.add_argument("--db_user", default="postgres", help="Nazwa użytkownika PostgreSQL")
    parser.add_argument("--db_password", default="password", help="Hasło do PostgreSQL")
    parser.add_argument("--db_host", default="localhost", help="Adres hosta PostgreSQL")
    parser.add_argument("--db_port", default="5432", help="Port PostgreSQL")
    parser.add_argument("--db_name", default="postgres", help="Nazwa bazy danych PostgreSQL")

    args = parser.parse_args()

    # Uruchomienie funkcji importującej
    import_csv_to_postgres(args.folder, args.db_user, args.db_password, args.db_host, args.db_port, args.db_name)