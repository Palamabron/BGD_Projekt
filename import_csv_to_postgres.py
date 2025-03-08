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

    # Iteracja po plikach w folderze
    for file in os.listdir(folder):
        if file.endswith('.csv'):
            table_name = os.path.splitext(file)[0]  # Nazwa tabeli to nazwa pliku (bez rozszerzenia)
            file_path = os.path.join(folder, file)

            try:
                # Wczytanie danych z CSV do DataFrame
                df = pd.read_csv(file_path)
                print(f"Importowanie danych z pliku '{file_path}' do tabeli '{table_name}'")

                # Zapisanie danych do bazy
                df.to_sql(table_name, engine, if_exists='replace', index=False)
                print(f"Tabela '{table_name}' została załadowana do bazy PostgreSQL.")

            except Exception as e:
                print(f"Błąd podczas importu pliku '{file_path}': {e}")

    print("Import zakończony.")

# Parsowanie argumentów wiersza poleceń
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import plików CSV do bazy PostgreSQL")
    
    parser.add_argument("--folder", default="csv_files", help="Ścieżka do folderu z plikami CSV")
    parser.add_argument("--db_user", default="postgres", help="Nazwa użytkownika PostgreSQL")
    parser.add_argument("--db_password", default="password", help="Hasło do PostgreSQL")
    parser.add_argument("--db_host", default="localhost", help="Adres hosta PostgreSQL")
    parser.add_argument("--db_port", default="5432", help="Port PostgreSQL")
    parser.add_argument("--db_name", default="postgres", help="Nazwa bazy danych PostgreSQL")

    args = parser.parse_args()

    # Uruchomienie funkcji importującej
    import_csv_to_postgres(args.folder, args.db_user, args.db_password, args.db_host, args.db_port, args.db_name)
