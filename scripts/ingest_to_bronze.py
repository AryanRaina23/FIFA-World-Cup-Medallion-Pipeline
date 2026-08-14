import os
import sys
import json
import uuid
import datetime
import pandas as pd
import xml.etree.ElementTree as ET
import psycopg2
from psycopg2.extras import execute_values

def get_connection():
    # Attempt to connect to PostgreSQL using different possible hosts
    hosts = ['postgres', 'localhost', '127.0.0.1']
    for host in hosts:
        try:
            conn = psycopg2.connect(
                host=host,
                database='fifa_dw',
                user='postgres',
                password='postgres',
                port=5432,
                connect_timeout=3
            )
            return conn
        except Exception:
            continue
    raise Exception("Unable to connect to PostgreSQL database.")

def log_to_run_history(run_id, pipeline_name, start_time):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO metadata.pipeline_runs (run_id, pipeline_name, start_time, status)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (run_id) DO UPDATE SET start_time = EXCLUDED.start_time;
            """,
            (run_id, pipeline_name, start_time, 'RUNNING')
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error logging pipeline run: {e}")
    finally:
        cur.close()
        conn.close()

def log_to_audit(run_id, step_name, table_name, processed, inserted, updated, rejected, status, error_msg=None):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO metadata.audit_logs 
            (run_id, step_name, table_name, records_processed, records_inserted, records_updated, records_rejected, status, error_message)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (run_id, step_name, table_name, processed, inserted, updated, rejected, status, error_msg)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error writing audit log: {e}")
    finally:
        cur.close()
        conn.close()

def parse_xml_to_df(xml_path):
    # Parses the custom XML structure of editions
    tree = ET.parse(xml_path)
    root = tree.getroot()
    records = []
    for ed_node in root.findall('edition'):
        row = {}
        for child in ed_node:
            row[child.tag] = child.text
        records.append(row)
    return pd.DataFrame(records)

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
BASE_DIR = os.environ.get("AIRFLOW_HOME", project_root)

def save_local_bronze_backup(df, table_name, run_id):
    today = datetime.date.today().isoformat()
    backup_dir = os.path.join(BASE_DIR, "data", "bronze", table_name, f"ingest_date={today}")
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, f"run_{run_id}.csv")
    df.to_csv(backup_path, index=False)
    print(f"Saved local bronze backup: {backup_path}")

def load_df_to_bronze_db(df, table_name, cur):
    # Truncate the raw staging table first to make it a fresh ingest
    cur.execute(f"TRUNCATE TABLE bronze.{table_name}_raw;")
    
    if df.empty:
        return 0

    columns = list(df.columns)
    col_str = ', '.join(['"' + str(c) + '"' for c in columns])
    query = f"INSERT INTO bronze.{table_name}_raw ({col_str}) VALUES %s"
    
    # Convert dataframe rows to tuples
    values = [tuple(x) for x in df.values]
    execute_values(cur, query, values)
    return len(df)

def main():
    # Generate run_id or use one passed by Airflow
    run_id = sys.argv[1] if len(sys.argv) > 1 else str(uuid.uuid4())
    start_time = datetime.datetime.now()
    
    log_to_run_history(run_id, "FIFA_WORLD_CUP_ETL", start_time)
    
    sources_dir = os.path.join(BASE_DIR, "data", "sources")
    
    sources = {
        "teams": {"file": "wc_2026_teams.json", "format": "JSON"},
        "fixtures": {"file": "wc_2026_fixtures.csv", "format": "CSV"},
        "editions": {"file": "wc_all_editions.json", "format": "JSON"},
        "matches": {"file": "wc_all_matches.csv", "format": "CSV"},
        "top_scorers": {"file": "wc_top_scorers.json", "format": "JSON"}
    }
    
    conn = get_connection()
    cur = conn.cursor()
    
    for table_name, info in sources.items():
        file_path = os.path.join(sources_dir, info["file"])
        print(f"\nIngesting {table_name} from {file_path} ({info['format']})")
        
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Source file {file_path} not found.")
            
            # Read files based on their format
            if info["format"] == "CSV":
                df = pd.read_csv(file_path)
            elif info["format"] == "JSON":
                df = pd.read_json(file_path)
            elif info["format"] == "XML":
                df = parse_xml_to_df(file_path)
            else:
                raise ValueError(f"Unknown format: {info['format']}")
            
            # Cast all columns to string for Bronze schema raw tables
            df = df.astype(str)
            
            # Clean column names to lowercase/trim spaces (though our datasets are clean)
            df.columns = [c.strip().lower() for c in df.columns]
            
            # Add metadata columns
            df['_ingestion_id'] = [str(uuid.uuid4()) for _ in range(len(df))]
            df['_ingested_at'] = datetime.datetime.now().isoformat()
            df['_source_file'] = info["file"]
            df['_source_format'] = info["format"]
            df['_run_id'] = run_id
            
            # Save raw local backup partitioned by date
            save_local_bronze_backup(df, table_name, run_id)
            
            # Load to raw database tables
            rows_loaded = load_df_to_bronze_db(df, table_name, cur)
            conn.commit()
            
            print(f"Loaded {rows_loaded} records to bronze.{table_name}_raw")
            log_to_audit(run_id, "INGESTION", f"bronze.{table_name}_raw", rows_loaded, rows_loaded, 0, 0, "SUCCESS")
            
        except Exception as e:
            conn.rollback()
            print(f"Failed to ingest {table_name}: {e}")
            log_to_audit(run_id, "INGESTION", f"bronze.{table_name}_raw", 0, 0, 0, 0, "FAILED", str(e))
            cur.close()
            conn.close()
            sys.exit(1)
            
    cur.close()
    conn.close()
    print("\nBronze ingestion completed successfully.")

if __name__ == "__main__":
    main()
