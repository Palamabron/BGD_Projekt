import os
import argparse
import pandas as pd
import logging
from sqlalchemy import create_engine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def import_csv_to_postgres(folder, db_user, db_password, db_host, db_port, db_name):
    connection_url = f'postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
    engine = create_engine(connection_url)
    
    if not os.path.exists(folder):
        logging.error(f"Folder '{folder}' does not exist.")
        return

    tables = {}
    
    for file in sorted(os.listdir(folder)):
        if file.endswith('.csv'):
            table_name = os.path.splitext(file)[0].rstrip("0123456789")
            file_path = os.path.join(folder, file)
            try:
                df = pd.read_csv(file_path)
                logging.info(f"Loading file '{file_path}' into table '{table_name}'")
                # Basic data validation: check if DataFrame is not empty
                if df.empty:
                    logging.warning(f"File '{file_path}' is empty. Skipping.")
                    continue
                
                if table_name in tables:
                    tables[table_name] = pd.concat([tables[table_name], df], ignore_index=True)
                else:
                    tables[table_name] = df
            except Exception as e:
                logging.error(f"Error loading file '{file_path}': {e}", exc_info=True)

    for table_name, df in tables.items():
        try:
            df.to_sql(table_name, engine, if_exists='append', index=False)
            logging.info(f"Data for table '{table_name}' has been inserted into PostgreSQL.")
        except Exception as e:
            logging.error(f"Error writing to table '{table_name}': {e}", exc_info=True)

    logging.info("CSV import completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import CSV files into PostgreSQL")
    parser.add_argument("--folder", required=True, help="Path to folder with CSV files")
    parser.add_argument("--db_user", default="postgres", help="PostgreSQL user")
    parser.add_argument("--db_password", default="password", help="PostgreSQL password")
    parser.add_argument("--db_host", default="localhost", help="PostgreSQL host")
    parser.add_argument("--db_port", default="5432", help="PostgreSQL port")
    parser.add_argument("--db_name", default="postgres", help="PostgreSQL database name")

    args = parser.parse_args()

    import_csv_to_postgres(args.folder, args.db_user, args.db_password, args.db_host, args.db_port, args.db_name)
